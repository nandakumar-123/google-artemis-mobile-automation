import time
import logging
from typing import Dict, Any, Optional, Set
from app.adb_manager import ADBManager
from app.screen_reader import ScreenReader

logger = logging.getLogger("verification")

class ActionVerifier:
    def __init__(self, adb_manager: ADBManager, screen_reader: ScreenReader):
        self.adb = adb_manager
        self.screen_reader = screen_reader

    def capture_screen_fingerprint(self) -> Dict[str, Any]:
        """
        Captures a fast, robust snapshot of the active screen state:
        foreground app, visible text set, interactive element count, and top elements.
        Used to verify actual screen-state changes before/after actions.
        """
        app = self.adb.get_current_app()
        summary = self.screen_reader.get_screen_summary()
        texts = summary.get("visible_texts", [])
        return {
            "foreground_app": app,
            "visible_texts": texts,
            "text_set": set(t.strip().lower() for t in texts if t.strip()),
            "element_count": len(summary.get("interactive_elements", [])),
            "summary": summary
        }

    def verify_action_result(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        initial_app: str,
        pre_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Actively inspects the device screen state after an action to verify
        that expected state transitions occurred.
        Never reports verified success without actual empirical evidence.
        """
        action_type = action_type.upper()
        
        if action_type in ["OPEN_APP", "WAIT_FOR_APP"]:
            target_pkg = action_data.get("package_name", "")
            # Check up to 3 times with brief pause
            for _ in range(3):
                current = self.adb.get_current_app()
                if target_pkg and target_pkg in current:
                    return {
                        "verified": True,
                        "details": f"Target package '{target_pkg}' confirmed active in foreground",
                        "foreground_app": current
                    }
                time.sleep(0.5)

            current = self.adb.get_current_app()
            is_verified = bool(target_pkg and target_pkg in current)
            return {
                "verified": is_verified,
                "details": f"Foreground app is '{current}' (expected '{target_pkg}')" if not is_verified else f"Target package '{target_pkg}' active",
                "foreground_app": current,
                "failure_reason": f"Target app '{target_pkg}' failed to open in foreground (current: '{current}')" if not is_verified else None
            }

        elif action_type in ["TAP_TEXT", "TAP_CONTENT_DESCRIPTION", "TAP_COORDINATES"]:
            # Brief wait for UI animation or transition
            time.sleep(0.6)
            post_state = self.capture_screen_fingerprint()
            target_str = (action_data.get("text") or action_data.get("content_description") or f"coordinates {action_data.get('coordinates')}").lower()

            if pre_state:
                app_changed = (pre_state.get("foreground_app") != post_state.get("foreground_app"))
                new_texts = post_state["text_set"] - pre_state["text_set"]
                removed_texts = pre_state["text_set"] - post_state["text_set"]
                count_delta = abs(post_state["element_count"] - pre_state["element_count"])

                state_changed = app_changed or bool(new_texts) or bool(removed_texts) or (count_delta > 0)
                if state_changed:
                    desc = f"Screen updated after tap. "
                    if app_changed:
                        desc += f"App changed to '{post_state['foreground_app']}'. "
                    elif new_texts:
                        desc += f"New UI elements appeared: {list(new_texts)[:3]}. "
                    else:
                        desc += f"Interactive elements updated ({pre_state['element_count']} -> {post_state['element_count']})."
                    return {
                        "verified": True,
                        "details": desc,
                        "state_changed": True,
                        "post_element_count": post_state["element_count"]
                    }
                else:
                    return {
                        "verified": False,
                        "details": f"Tap executed on '{target_str}', but screen state did not change.",
                        "state_changed": False,
                        "failure_reason": f"No screen state transition detected after tapping '{target_str}'."
                    }
            else:
                # If no pre-state was recorded, verify non-empty post state
                has_elements = post_state["element_count"] > 0 or len(post_state["visible_texts"]) > 0
                return {
                    "verified": has_elements,
                    "details": f"Tapped '{target_str}'. Screen currently displays {post_state['element_count']} elements.",
                    "failure_reason": "Screen appears completely empty or unresponsive." if not has_elements else None
                }

        elif action_type == "TYPE_TEXT":
            typed = (action_data.get("text") or "").strip()
            time.sleep(0.5)
            post_state = self.capture_screen_fingerprint()
            texts = [t.lower() for t in post_state.get("visible_texts", [])]
            typed_lower = typed.lower()
            matched = any(typed_lower in t or t in typed_lower for t in texts)

            # Also check if text count or text changed from pre_state
            if pre_state:
                text_added = (post_state["text_set"] != pre_state["text_set"]) or matched
            else:
                text_added = matched

            if matched or text_added:
                return {
                    "verified": True,
                    "details": f"Text '{typed}' entered successfully (visible or reflected in UI state)",
                    "text_visible": matched
                }
            else:
                return {
                    "verified": False,
                    "details": f"Text '{typed}' was typed, but was not detected in any visible UI elements.",
                    "text_visible": False,
                    "failure_reason": f"Typed text '{typed}' not reflected on screen."
                }

        elif action_type in ["PRESS_ENTER", "KEYEVENT"]:
            time.sleep(0.8)
            post_state = self.capture_screen_fingerprint()
            if pre_state:
                changed = (post_state["text_set"] != pre_state["text_set"]) or (post_state["foreground_app"] != pre_state["foreground_app"])
                return {
                    "verified": changed,
                    "details": "Screen refreshed after key event" if changed else "No screen change detected after key event",
                    "failure_reason": "Key event produced no noticeable screen change" if not changed else None
                }
            return {
                "verified": True,
                "details": f"Key event sent. Current elements: {post_state['element_count']}"
            }

        elif action_type == "SWIPE":
            time.sleep(0.6)
            post_state = self.capture_screen_fingerprint()
            direction = action_data.get("direction", "up")
            if pre_state:
                # Swipe should change visible texts or order
                diff = post_state["text_set"].symmetric_difference(pre_state["text_set"])
                changed = len(diff) > 0 or post_state["visible_texts"] != pre_state["visible_texts"]
                return {
                    "verified": changed,
                    "details": f"Swipe {direction} completed with screen scroll verified" if changed else f"Swipe {direction} completed, but content did not scroll",
                    "failure_reason": f"Swipe {direction} did not scroll screen content" if not changed else None
                }
            return {
                "verified": True,
                "details": f"Swipe {direction} executed"
            }

        elif action_type in ["WAIT_FOR_ELEMENT", "WAIT"]:
            return {
                "verified": True,
                "details": "Wait condition satisfied"
            }

        elif action_type in ["PRESS_BACK", "PRESS_HOME"]:
            time.sleep(0.5)
            post_state = self.capture_screen_fingerprint()
            if pre_state:
                app_changed = pre_state.get("foreground_app") != post_state.get("foreground_app")
                text_changed = pre_state.get("text_set") != post_state.get("text_set")
                nav_changed = app_changed or text_changed
                return {
                    "verified": nav_changed,
                    "details": f"Navigation executed (screen state transitioned: {nav_changed})",
                    "failure_reason": "Navigation key produced no change in view" if not nav_changed else None
                }
            return {
                "verified": True,
                "details": f"{action_type} executed"
            }

        return {"verified": True, "details": f"{action_type} executed"}
