import re
import logging
from typing import Dict, Any, List, Optional
from app.schemas import ActionPlan, ActionItem
from app.gemini_service import GeminiService
from app.config import MAX_ACTION_STEPS

logger = logging.getLogger("action_planner")

VALID_ACTION_TYPES = {
    "OPEN_APP", "WAIT_FOR_APP", "WAIT_FOR_ELEMENT", "TAP_TEXT",
    "TAP_CONTENT_DESCRIPTION", "TAP_COORDINATES", "TYPE_TEXT",
    "PRESS_ENTER", "KEYEVENT", "SWIPE", "PRESS_BACK", "PRESS_HOME",
    "WAIT", "TAKE_SCREENSHOT", "READ_SCREEN", "ASK_CONFIRMATION"
}

class ActionPlanner:
    def __init__(self, gemini_service: GeminiService):
        self.gemini_service = gemini_service

    def plan(self, instruction: str, current_screen_info: Dict[str, Any], current_app: str) -> ActionPlan:
        # Check for sensitive action requests early
        if self._is_sensitive_request(instruction):
            return ActionPlan(
                task=instruction,
                actions=[
                    ActionItem(type="ASK_CONFIRMATION", reason=f"The requested action '{instruction}' involves security or sensitive operations.")
                ],
                requires_confirmation=True,
                confirmation_message=f"Are you sure you want to execute: '{instruction}'? This might modify data, send messages, or perform sensitive changes."
            )

        plan = None
        # 1. Try Gemini AI Planner if configured
        if self.gemini_service.is_configured():
            try:
                gemini_plan = self.gemini_service.plan_automation(instruction, current_screen_info, current_app)
                if gemini_plan and gemini_plan.actions:
                    plan = gemini_plan
            except Exception as e:
                logger.error(f"Gemini planning failed: {e}")

        # 2. Robust Rule-Based Planner Fallback
        if not plan or not plan.actions:
            plan = self._rule_based_plan(instruction, current_screen_info)

        # 3. Validate and sanitize plan steps
        return self._validate_and_sanitize_plan(plan, instruction)

    def _is_sensitive_request(self, instruction: str) -> bool:
        low = instruction.lower()
        sensitive_patterns = [
            r"\b(pay|payment|upi|gpay|phonepe|send money|transfer)\b",
            r"\b(delete|remove|erase|format)\b",
            r"\b(uninstall)\b",
            r"\b(send (message|sms|whatsapp|chat))\b",
            r"\b(call|dial|make call)\b",
            r"\b(reset|factory reset)\b",
            r"\b(change password|security settings)\b"
        ]
        return any(re.search(pat, low) for pat in sensitive_patterns)

    def _validate_and_sanitize_plan(self, plan: ActionPlan, instruction: str) -> ActionPlan:
        """
        Validates action types, injects needed waits, enforces MAX_ACTION_STEPS.
        """
        valid_actions: List[ActionItem] = []
        for action in plan.actions:
            act_type = action.type.upper()
            if act_type not in VALID_ACTION_TYPES:
                logger.warning(f"Dropping unknown action type: {act_type}")
                continue
            action.type = act_type
            valid_actions.append(action)

        if not valid_actions:
            # Fallback action
            valid_actions = [ActionItem(type="READ_SCREEN")]

        # Enforce MAX_ACTION_STEPS limit
        status = "valid"
        notes = None
        if len(valid_actions) > MAX_ACTION_STEPS:
            logger.warning(f"Action plan exceeded safe limit {MAX_ACTION_STEPS}. Truncating.")
            valid_actions = valid_actions[:MAX_ACTION_STEPS]
            status = "clamped"
            notes = f"Plan steps clamped to safe limit of {MAX_ACTION_STEPS}"

        plan.actions = valid_actions
        plan.validation_status = status
        plan.notes = notes
        return plan

    def _rule_based_plan(self, instruction: str, current_screen_info: Dict[str, Any]) -> ActionPlan:
        low = instruction.lower().strip()
        actions: List[ActionItem] = []

        # Complex YouTube query pattern: "open youtube, search for ... open the first relevant video and play it"
        if "youtube" in low:
            # Check for search
            search_query = ""
            for pattern in [
                r"search (?:for|about)?\s+([^,]+?)(?:,|$|\s+open|\s+and)",
                r"find (?:for)?\s+([^,]+?)(?:,|$|\s+open|\s+and)",
                r"search\s+(.+)"
            ]:
                match = re.search(pattern, low)
                if match:
                    search_query = match.group(1).strip()
                    break

            if not search_query and "search" in low:
                # Fallback extract
                parts = low.split("search")
                if len(parts) > 1:
                    raw_q = parts[1].replace("for", "").strip()
                    for end_word in ["and open", "open the", "play it", "then play"]:
                        if end_word in raw_q:
                            raw_q = raw_q.split(end_word)[0].strip()
                    search_query = raw_q

            actions.append(ActionItem(
                type="OPEN_APP",
                app_name="YouTube",
                package_name="com.google.android.youtube"
            ))
            actions.append(ActionItem(
                type="WAIT_FOR_APP",
                package_name="com.google.android.youtube",
                timeout=6.0
            ))
            actions.append(ActionItem(
                type="WAIT",
                seconds=1.5
            ))

            if search_query:
                # Tap Search button
                actions.append(ActionItem(
                    type="TAP_CONTENT_DESCRIPTION",
                    content_description="Search",
                    fallback_text="Search",
                    fallback_content_description="Search YouTube"
                ))
                actions.append(ActionItem(
                    type="WAIT",
                    seconds=1.0
                ))
                # Type query
                actions.append(ActionItem(
                    type="TYPE_TEXT",
                    text=search_query
                ))
                # Press Enter to submit search
                actions.append(ActionItem(
                    type="PRESS_ENTER"
                ))
                # Wait for search results
                actions.append(ActionItem(
                    type="WAIT",
                    seconds=2.5
                ))

                # If user asked to open / play first video
                if any(w in low for w in ["open", "play", "first", "video"]):
                    # First video item in search results:
                    # YouTube videos typically have content descriptions containing "ago", "views", "Go to channel", or the title
                    actions.append(ActionItem(
                        type="TAP_CONTENT_DESCRIPTION",
                        content_description="views",
                        fallback_content_description="ago",
                        fallback_text=search_query.split()[0] if search_query else None,
                        match_index=0
                    ))
                    actions.append(ActionItem(
                        type="WAIT",
                        seconds=2.0
                    ))
                    # Screen check
                    actions.append(ActionItem(
                        type="TAKE_SCREENSHOT"
                    ))

            return ActionPlan(task=instruction, actions=actions)

        # Chrome search pattern
        if "chrome" in low and ("search" in low or "open" in low):
            query = ""
            if "search" in low:
                query = low.split("search", 1)[1].replace("for", "").strip()
            actions.append(ActionItem(type="OPEN_APP", app_name="Chrome", package_name="com.android.chrome"))
            actions.append(ActionItem(type="WAIT_FOR_APP", package_name="com.android.chrome", timeout=5.0))
            if query:
                actions.append(ActionItem(type="TAP_TEXT", text="Search or type URL", fallback_content_description="Search or type URL"))
                actions.append(ActionItem(type="TYPE_TEXT", text=query))
                actions.append(ActionItem(type="PRESS_ENTER"))
                actions.append(ActionItem(type="WAIT", seconds=2.0))
            return ActionPlan(task=instruction, actions=actions)

        # Open Play Store
        if "play store" in low:
            actions.append(ActionItem(type="OPEN_APP", app_name="Play Store", package_name="com.android.vending"))
            actions.append(ActionItem(type="WAIT_FOR_APP", package_name="com.android.vending", timeout=5.0))
            return ActionPlan(task=instruction, actions=actions)

        # Open settings
        if "settings" in low:
            actions.append(ActionItem(type="OPEN_APP", app_name="Settings", package_name="com.android.settings"))
            actions.append(ActionItem(type="WAIT_FOR_APP", package_name="com.android.settings", timeout=5.0))
            if "battery" in low:
                actions.append(ActionItem(type="TAP_TEXT", text="Battery", fallback_content_description="Battery"))
            elif "display" in low:
                actions.append(ActionItem(type="TAP_TEXT", text="Display", fallback_content_description="Display"))
            return ActionPlan(task=instruction, actions=actions)

        # Navigation
        if "back" in low or "previous screen" in low:
            actions.append(ActionItem(type="PRESS_BACK"))
            return ActionPlan(task=instruction, actions=actions)

        if "home" in low or "go home" in low:
            actions.append(ActionItem(type="PRESS_HOME"))
            return ActionPlan(task=instruction, actions=actions)

        # Scrolling / Swiping
        if "scroll down" in low or "swipe down" in low or "swipe up" in low:
            actions.append(ActionItem(type="SWIPE", direction="up"))
            if "display" in low:
                actions.append(ActionItem(type="WAIT", seconds=1.0))
                actions.append(ActionItem(type="TAP_TEXT", text="Display"))
            return ActionPlan(task=instruction, actions=actions)

        if "scroll up" in low:
            actions.append(ActionItem(type="SWIPE", direction="down"))
            return ActionPlan(task=instruction, actions=actions)

        # Screen capture
        if "screenshot" in low or "capture" in low or "read screen" in low:
            actions.append(ActionItem(type="TAKE_SCREENSHOT"))
            actions.append(ActionItem(type="READ_SCREEN"))
            return ActionPlan(task=instruction, actions=actions)

        # Generic Tap text
        words = low.replace("tap", "").replace("click", "").strip()
        actions.append(ActionItem(type="TAP_TEXT", text=words.title(), fallback_content_description=words))
        return ActionPlan(task=instruction, actions=actions)
