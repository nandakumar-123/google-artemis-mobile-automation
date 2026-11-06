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

            # Pre-action screen state capture for robust verification
            pre_state = self.verifier.capture_screen_fingerprint()
            current_action_target = action

            max_recovery_attempts = min(action.retry_count if action.retry_count is not None else MAX_RETRIES_PER_STEP, 2)
            recovery_count = 0
            action_result = None
            verification = None

            while True:
                if self.executor.stop_requested:
                    action_result = {"action": current_action_target.type, "status": "stopped", "message": "Automation stopped by user"}
                    break

                # 1. Execute target action
                action_result = self.executor.execute_action(current_action_target)

                # If stopped mid-action, exit early
                if action_result.get("status") == "stopped" or self.executor.stop_requested:
                    break

                # 2. Verify screen state change
                current_app = self.adb.get_current_app()
                verification = self.verifier.verify_action_result(
                    action_type=current_action_target.type,
                    action_data=current_action_target.model_dump(),
                    initial_app=pre_state.get("foreground_app", ""),
                    pre_state=pre_state
                )

                # Determine if execution and verification both succeeded
                exec_ok = (action_result.get("status") == "success")
                verify_ok = verification.get("verified", False)

                if exec_ok and verify_ok:
                    action_result["status"] = "success"
                    break

                # If execution failed or verification failed, attempt self-healing recovery if quota remains
                if recovery_count < max_recovery_attempts:
                    recovery_count += 1
                    failure_reason = action_result.get("message") or verification.get("failure_reason") or "Action executed but screen state did not change."
                    logger.warning(
                        f"Step {idx+1} failed verification or execution (recovery attempt {recovery_count}/{max_recovery_attempts}): {failure_reason}"
                    )

                    # Update progress UI with recovery status
                    if self.active_progress:
                        self.active_progress.current_action = f"{step_desc} [Self-Healing Attempt {recovery_count}/{max_recovery_attempts}]"

                    # Capture updated live UI state and screenshot for Gemini recovery planner
                    time.sleep(1.0)
                    latest_screen_info = self.screen_reader.get_screen_summary()
                    latest_screenshot = self.screen_reader.capture_screenshot()
                    latest_app = self.adb.get_current_app()

                    recovered_action = None
                    try:
                        recovered_action = self.gemini.plan_recovery_action(
                            instruction=instruction,
                            failed_action=current_action_target.model_dump(),
                            failure_reason=failure_reason,
                            current_screen_info=latest_screen_info,
                            current_app=latest_app,
                            screenshot_path=latest_screenshot
                        )
                    except Exception as rec_err:
                        logger.error(f"Error during AI recovery generation: {rec_err}")

                    if recovered_action:
                        logger.info(f"Self-Healing generated corrected action: {recovered_action.type} ({recovered_action.reason or ''})")
                        current_action_target = recovered_action
                        # Reset pre_state to current screen before executing recovery action
                        pre_state = self.verifier.capture_screen_fingerprint()
                        continue
                    else:
                        # Fallback heuristic: small pause and retry
                        time.sleep(1.2)
                        pre_state = self.verifier.capture_screen_fingerprint()
                        continue
                else:
                    # Maximum recovery attempts exhausted
                    if not exec_ok:
                        action_result["status"] = "failed"
                    elif not verify_ok:
                        action_result["status"] = "failed"
                        action_result["message"] = verification.get("failure_reason") or "Verification failed: screen state did not change."
                    break

            if not action_result:
                action_result = {"action": action.type, "status": "failed", "message": "Unknown execution error"}

            if verification:
                action_result["verification"] = verification
            action_result["step_index"] = idx + 1
            action_result["step_description"] = step_desc
            action_result["recovery_attempts"] = recovery_count
            if recovery_count > 0:
                action_result["recovery_details"] = f"{recovery_count}/{max_recovery_attempts} self-healing attempts made"

            executed_actions.append(action_result)

            if action_result.get("status") in ["failed", "error"]:
                overall_success = False
                error_msg = action_result.get("message") or action_result.get("error") or f"{action.type} failed after {recovery_count} recovery attempts"
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
