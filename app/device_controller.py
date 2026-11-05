import time
import logging
from typing import Dict, Any, Optional, List
from app.adb_manager import ADBManager
from app.screen_reader import ScreenReader
from app.gemini_service import GeminiService
from app.action_planner import ActionPlanner
from app.action_executor import ActionExecutor
from app.verification import ActionVerifier
from app.database import save_task, update_task
from app.schemas import ActionPlan, ActionItem, TaskProgress
from app.config import MAX_ACTION_STEPS, MAX_RETRIES_PER_STEP

logger = logging.getLogger("device_controller")

class DeviceController:
    def __init__(self):
        self.adb = ADBManager()
        self.screen_reader = ScreenReader(self.adb)
        self.gemini = GeminiService()
        self.planner = ActionPlanner(self.gemini)
        self.executor = ActionExecutor(self.adb, self.screen_reader)
        self.verifier = ActionVerifier(self.adb, self.screen_reader)
        self.is_busy = False
        self.pending_confirmation: Optional[Dict[str, Any]] = None
        self.active_progress: Optional[TaskProgress] = None

    def get_status(self) -> Dict[str, Any]:
        status_info = self.adb.check_connection_status()
        if status_info.get("connected"):
            status_info["current_app"] = self.adb.get_current_app()
        return status_info

    def get_progress(self) -> Optional[Dict[str, Any]]:
        if self.active_progress:
            return self.active_progress.model_dump()
        return None

    def select_device(self, serial: str) -> bool:
        return self.adb.set_selected_device(serial)

    def pair_wireless(self, ip: str, port: int, code: str) -> Dict[str, Any]:
        success, message = self.adb.pair_device(ip, port, code)
        return {"success": success, "message": message}

    def pair_with_qr(self, qr_payload: str, phone_ip: Optional[str] = None) -> Dict[str, Any]:
        success, message, detected_ip, detected_port = self.adb.pair_with_qr(qr_payload, phone_ip)
        return {
            "success": success,
            "message": message,
            "ip": detected_ip,
            "port": detected_port
        }

    def connect_wireless(self, ip: str, port: int) -> Dict[str, Any]:
        success, message = self.adb.connect_device(ip, port)
        return {"success": success, "message": message}

    def disconnect_wireless(self, target: Optional[str] = None) -> Dict[str, Any]:
        success, message = self.adb.disconnect_device(target)
        return {"success": success, "message": message}

    def get_latest_screenshot(self) -> Optional[str]:
        return self.screen_reader.capture_screenshot()

    def stop_execution(self):
        logger.info("Immediate stop requested for automation task.")
        self.executor.request_stop()
        if self.active_progress:
            self.active_progress.status = "cancelled"
            self.active_progress.error_message = "Cancelled by user"
        self.is_busy = False
        self.pending_confirmation = None

    def execute_instruction(self, instruction: str) -> Dict[str, Any]:
        if self.is_busy:
            return {
                "task_id": -1,
                "instruction": instruction,
                "success": False,
                "message": "Another automation task is currently in progress. Please wait or click Stop.",
                "actions_executed": []
            }

        self.is_busy = True
        self.executor.stop_requested = False

        # Verify device connection
        device_status = self.adb.check_connection_status()
        if not device_status["connected"]:
            self.is_busy = False
            task_id = save_task(instruction=instruction, success=False, error_message=device_status["status"])
            return {
                "task_id": task_id,
                "instruction": instruction,
                "success": False,
                "message": device_status["status"],
                "actions_executed": []
            }

        # Screen state before planning
        current_app = self.adb.get_current_app()
        current_screen_info = self.screen_reader.get_screen_summary()

        # Plan actions
        plan: ActionPlan = self.planner.plan(instruction, current_screen_info, current_app)
        task_id = save_task(instruction=instruction, plan=plan.model_dump())

        # Check safety confirmation
        if plan.requires_confirmation:
            self.pending_confirmation = {
                "task_id": task_id,
                "instruction": instruction,
                "plan": plan
            }
            self.is_busy = False
            return {
                "task_id": task_id,
                "instruction": instruction,
                "success": True,
                "message": plan.confirmation_message or "Confirmation required before proceeding with this sensitive task.",
                "requires_confirmation": True,
                "pending_action": plan.actions[0] if plan.actions else None,
                "actions_executed": []
            }

        # Initialize progress tracker
        self.active_progress = TaskProgress(
            task_id=task_id,
            instruction=instruction,
            status="running",
            total_steps=len(plan.actions),
            current_step_index=0,
            completed_steps=[],
            failed_steps=[]
        )

        return self._run_action_sequence(task_id, instruction, plan.actions)

    def _run_action_sequence(self, task_id: int, instruction: str, actions: List[ActionItem]) -> Dict[str, Any]:
        executed_actions = []
        overall_success = True
        error_msg = None

        total_actions = len(actions)

        for idx, action in enumerate(actions):
            if self.executor.stop_requested:
                error_msg = "Task execution was cancelled by user."
                overall_success = False
                if self.active_progress:
                    self.active_progress.status = "cancelled"
                    self.active_progress.error_message = error_msg
                break

            step_desc = f"Step {idx+1}/{total_actions}: {action.type}"
            if action.text:
                step_desc += f" ('{action.text}')"
            elif action.content_description:
                step_desc += f" ('{action.content_description}')"
            elif action.package_name:
                step_desc += f" ({action.package_name})"

            if self.active_progress:
                self.active_progress.current_step_index = idx + 1
                self.active_progress.current_action = step_desc

            logger.info(f"Sequential Execution -> {step_desc}")

            # Execution with error recovery retry
            max_retries = action.retry_count if action.retry_count is not None else MAX_RETRIES_PER_STEP
            attempt = 0
            action_result = None

            while attempt <= max_retries:
                if self.executor.stop_requested:
                    break

                action_result = self.executor.execute_action(action)
                
                # Check result status
                if action_result.get("status") == "success":
                    break
                elif action_result.get("status") == "stopped":
                    break
                else:
                    attempt += 1
                    if attempt <= max_retries:
                        logger.warning(f"Action {action.type} failed (attempt {attempt}/{max_retries}). Inspecting screen & retrying...")
                        # Screen recovery: pause and inspect UI
                        time.sleep(1.0)
                        # If app wasn't in foreground, try re-focusing or waiting
                        if action.type in ["TAP_TEXT", "TAP_CONTENT_DESCRIPTION"]:
                            time.sleep(1.2)

            if not action_result:
                action_result = {"action": action.type, "status": "failed", "message": "Unknown execution error"}

            # Screen Verification after important actions
            current_app = self.adb.get_current_app()
            verification = self.verifier.verify_action_result(action.type, action.model_dump(), current_app)
            action_result["verification"] = verification
            action_result["step_index"] = idx + 1
            action_result["step_description"] = step_desc

            executed_actions.append(action_result)

            if action_result.get("status") in ["failed", "error"]:
                overall_success = False
                error_msg = action_result.get("message") or action_result.get("error") or f"{action.type} failed after retries"
                if self.active_progress:
                    self.active_progress.failed_steps.append(action_result)
                break
            elif action_result.get("status") == "stopped":
                overall_success = False
                error_msg = "Automation stopped by user"
                break
            else:
                if self.active_progress:
                    self.active_progress.completed_steps.append(action_result)

        # Final screen capture
        final_screenshot = self.screen_reader.capture_screenshot()
        update_task(task_id, results=executed_actions, success=overall_success, error_message=error_msg, screenshot_path=final_screenshot)

        if self.active_progress:
            self.active_progress.status = "completed" if overall_success else ("cancelled" if self.executor.stop_requested else "failed")
            self.active_progress.error_message = error_msg

        self.is_busy = False

        return {
            "task_id": task_id,
            "instruction": instruction,
            "success": overall_success,
            "message": "Task completed successfully" if overall_success else (error_msg or "Task failed halfway"),
            "actions_executed": executed_actions,
            "screenshot_url": "/api/device/screenshot" if final_screenshot else None
        }

    def process_confirmation(self, task_id: int, approved: bool) -> Dict[str, Any]:
        if not self.pending_confirmation or self.pending_confirmation["task_id"] != task_id:
            return {"task_id": task_id, "success": False, "message": "No matching pending confirmation found."}

        pending = self.pending_confirmation
        self.pending_confirmation = None

        if not approved:
            update_task(task_id, success=False, error_message="User rejected the confirmation prompt.")
            return {"task_id": task_id, "success": False, "message": "Action cancelled by user."}

        self.is_busy = True
        self.executor.stop_requested = False

        filtered_actions = [a for a in pending["plan"].actions if a.type != "ASK_CONFIRMATION"]

        self.active_progress = TaskProgress(
            task_id=task_id,
            instruction=pending["instruction"],
            status="running",
            total_steps=len(filtered_actions),
            current_step_index=0,
            completed_steps=[],
            failed_steps=[]
        )

        return self._run_action_sequence(task_id, pending["instruction"], filtered_actions)
