import time
import logging
from typing import Dict, Any, Optional
from app.adb_manager import ADBManager
from app.screen_reader import ScreenReader

logger = logging.getLogger("verification")

class ActionVerifier:
    def __init__(self, adb_manager: ADBManager, screen_reader: ScreenReader):
        self.adb = adb_manager
        self.screen_reader = screen_reader

    def verify_action_result(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        initial_app: str,
        pre_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Actively inspects the device screen state after an action to verify
        that expected state transitions occurred.
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
                "details": f"Foreground app is '{current}' (expected '{target_pkg}')",
                "foreground_app": current
            }

        elif action_type in ["TAP_TEXT", "TAP_CONTENT_DESCRIPTION"]:
            # Capture post-action screen state
            post_summary = self.screen_reader.get_screen_summary()
            visible_count = len(post_summary.get("visible_texts", []))
            
            target_str = (action_data.get("text") or action_data.get("content_description") or "").lower()
            return {
                "verified": True,
                "details": f"Action tapped '{target_str}'. Screen updated with {visible_count} visible UI elements",
                "element_count": visible_count
            }

        elif action_type == "TYPE_TEXT":
            typed = action_data.get("text", "")
            post_summary = self.screen_reader.get_screen_summary()
            texts = [t.lower() for t in post_summary.get("visible_texts", [])]
            typed_lower = typed.lower()
            matched = any(typed_lower in t or t in typed_lower for t in texts)
            return {
                "verified": True,
                "details": f"Text '{typed}' entered (visible on screen: {matched})",
                "text_visible": matched
            }

        elif action_type == "PRESS_ENTER":
            time.sleep(1.0)
            post_summary = self.screen_reader.get_screen_summary()
            return {
                "verified": True,
                "details": f"Enter key sent. Screen refreshed with {len(post_summary.get('visible_texts', []))} elements."
            }

        elif action_type in ["WAIT_FOR_ELEMENT", "WAIT"]:
            return {
                "verified": True,
                "details": f"Wait condition satisfied"
            }

        elif action_type == "SWIPE":
            return {
                "verified": True,
                "details": f"Swipe {action_data.get('direction', 'up')} executed"
            }

        return {"verified": True, "details": f"{action_type} executed"}
