import time
import logging
from typing import Dict, Any, List, Optional
from app.adb_manager import ADBManager
from app.screen_reader import ScreenReader
from app.schemas import ActionItem

logger = logging.getLogger("action_executor")

class ActionExecutor:
    def __init__(self, adb_manager: ADBManager, screen_reader: ScreenReader):
        self.adb = adb_manager
        self.screen_reader = screen_reader
        self.stop_requested = False

    def request_stop(self):
        self.stop_requested = True

    def execute_action(self, action: ActionItem) -> Dict[str, Any]:
        if self.stop_requested:
            return {"action": action.type, "status": "stopped", "message": "Automation stopped by user"}

        action_type = action.type.upper()
        logger.info(f"Executing action: {action_type} with details: {action.model_dump()}")

        try:
            if action_type == "OPEN_APP":
                if not action.package_name:
                    return {"action": action_type, "status": "failed", "message": "No package_name specified"}
                success = self.adb.open_app(action.package_name)
                # Wait briefly for app process to spawn
                time.sleep(1.0)
                return {"action": action_type, "status": "success" if success else "failed", "package": action.package_name}

            elif action_type == "TAP_TEXT":
                target_text = action.text
                if not target_text:
                    return {"action": action_type, "status": "failed", "message": "No text specified"}

                # Dynamic UI detection using screen_reader
                target = self.screen_reader.find_element(
                    text=target_text,
                    resource_id=action.resource_id,
                    class_name=action.class_name,
                    match_index=action.match_index or 0
                )
                
                # Fallback to secondary text or content description if primary not matched
                if not target and action.fallback_text:
                    target = self.screen_reader.find_element(text=action.fallback_text)
                if not target and action.content_description:
                    target = self.screen_reader.find_element(content_desc=action.content_description)

                if target:
                    x, y = target.center
                    success = self.adb.tap(x, y)
                    return {
                        "action": action_type,
                        "status": "success" if success else "failed",
                        "coordinates": [x, y],
                        "matched_text": target.text,
                        "matched_desc": target.content_desc
                    }
                return {"action": action_type, "status": "failed", "message": f"Text '{target_text}' not found on screen"}

            elif action_type == "TAP_CONTENT_DESCRIPTION":
                desc = action.content_description
                if not desc:
                    return {"action": action_type, "status": "failed", "message": "No content_description specified"}

                target = self.screen_reader.find_element(
                    content_desc=desc,
                    resource_id=action.resource_id,
                    class_name=action.class_name,
                    match_index=action.match_index or 0
                )

                # Fallback to text or fallback_content_description
                if not target and action.fallback_content_description:
                    target = self.screen_reader.find_element(content_desc=action.fallback_content_description)
                if not target and action.text:
                    target = self.screen_reader.find_element(text=action.text)

                if target:
                    x, y = target.center
                    success = self.adb.tap(x, y)
                    return {
                        "action": action_type,
                        "status": "success" if success else "failed",
                        "coordinates": [x, y],
                        "matched_desc": target.content_desc,
                        "matched_text": target.text
                    }
                return {"action": action_type, "status": "failed", "message": f"Content description '{desc}' not found on screen"}

            elif action_type == "TAP_COORDINATES":
                if action.x is None or action.y is None:
                    return {"action": action_type, "status": "failed", "message": "Coordinates x and y are required"}
                success = self.adb.tap(action.x, action.y)
                return {"action": action_type, "status": "success" if success else "failed", "coordinates": [action.x, action.y]}

            elif action_type == "TYPE_TEXT":
                if not action.text:
                    return {"action": action_type, "status": "failed", "message": "No text specified"}
                success = self.adb.type_text(action.text)
                return {"action": action_type, "status": "success" if success else "failed", "typed_text": action.text}

            elif action_type == "PRESS_ENTER":
                success = self.adb.press_enter()
                return {"action": action_type, "status": "success" if success else "failed"}

            elif action_type == "KEYEVENT":
                keycode = action.keycode or 66
                success = self.adb.keyevent(keycode)
                return {"action": action_type, "status": "success" if success else "failed", "keycode": keycode}

            elif action_type == "WAIT_FOR_APP":
                target_pkg = action.package_name
                timeout = action.timeout or 8.0
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.stop_requested:
                        return {"action": action_type, "status": "stopped", "message": "Cancelled"}
                    current = self.adb.get_current_app()
                    if target_pkg and target_pkg in current:
                        return {"action": action_type, "status": "success", "package": target_pkg, "waited": round(time.time() - start_time, 2)}
                    time.sleep(0.5)
                return {"action": action_type, "status": "failed", "message": f"App '{target_pkg}' did not open within {timeout}s"}

            elif action_type == "WAIT_FOR_ELEMENT":
                timeout = action.timeout or 10.0
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.stop_requested:
                        return {"action": action_type, "status": "stopped", "message": "Cancelled"}
                    
                    found = self.screen_reader.find_element(
                        text=action.text,
                        content_desc=action.content_description,
                        resource_id=action.resource_id,
                        match_index=action.match_index or 0
                    )
                    if found:
                        return {
                            "action": action_type,
                            "status": "success",
                            "matched": found.text or found.content_desc,
                            "waited": round(time.time() - start_time, 2)
                        }
                    time.sleep(0.8)

                return {"action": action_type, "status": "failed", "message": f"Element '{action.text or action.content_description}' not found within {timeout}s"}

            elif action_type == "SWIPE":
                direction = (action.direction or "up").lower()
                # Query actual screen size or default to 1080x2400
                screen_w, screen_h = self.adb.get_screen_size()
                mid_x = screen_w // 2

                if direction == "up":
                    # Swipe up scrolls down
                    start_x, start_y = mid_x, int(screen_h * 0.75)
                    end_x, end_y = mid_x, int(screen_h * 0.25)
                elif direction == "down":
                    start_x, start_y = mid_x, int(screen_h * 0.25)
                    end_x, end_y = mid_x, int(screen_h * 0.75)
                elif direction == "left":
                    start_x, start_y = int(screen_w * 0.85), int(screen_h * 0.5)
                    end_x, end_y = int(screen_w * 0.15), int(screen_h * 0.5)
                elif direction == "right":
                    start_x, start_y = int(screen_w * 0.15), int(screen_h * 0.5)
                    end_x, end_y = int(screen_w * 0.85), int(screen_h * 0.5)
                else:
                    start_x, start_y, end_x, end_y = mid_x, int(screen_h * 0.7), mid_x, int(screen_h * 0.3)

                success = self.adb.swipe(start_x, start_y, end_x, end_y)
                return {"action": action_type, "status": "success" if success else "failed", "direction": direction}

            elif action_type == "PRESS_BACK":
                success = self.adb.keyevent(4) # KEYCODE_BACK
                return {"action": action_type, "status": "success" if success else "failed"}

            elif action_type == "PRESS_HOME":
                success = self.adb.keyevent(3) # KEYCODE_HOME
                return {"action": action_type, "status": "success" if success else "failed"}

            elif action_type == "WAIT":
                duration = min(action.seconds or 1.0, 15.0)
                # Sleep in increments of 0.2s so cancellation stops immediately
                step = 0.2
                elapsed = 0.0
                while elapsed < duration:
                    if self.stop_requested:
                        return {"action": action_type, "status": "stopped", "message": "Cancelled"}
                    time.sleep(min(step, duration - elapsed))
                    elapsed += step
                return {"action": action_type, "status": "success", "seconds": duration}

            elif action_type == "TAKE_SCREENSHOT":
                path = self.screen_reader.capture_screenshot()
                return {"action": action_type, "status": "success" if path else "failed", "screenshot_path": path}

            elif action_type == "READ_SCREEN":
                summary = self.screen_reader.get_screen_summary()
                return {"action": action_type, "status": "success", "extracted_text_count": len(summary["visible_texts"])}

            elif action_type == "ASK_CONFIRMATION":
                return {"action": action_type, "status": "awaiting_confirmation", "reason": action.reason}

            else:
                return {"action": action_type, "status": "failed", "message": f"Unsupported action type: {action_type}"}

        except Exception as e:
            logger.error(f"Execution error for action {action_type}: {e}")
            return {"action": action_type, "status": "error", "error": str(e)}
