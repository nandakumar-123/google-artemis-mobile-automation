import json
import logging
from typing import Optional, Dict, Any
from app.config import GEMINI_API_KEY, GEMINI_MODEL, MAX_ACTION_STEPS
from app.schemas import ActionPlan, ActionItem

logger = logging.getLogger("gemini_service")

class GeminiService:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model_name = model_name or GEMINI_MODEL
        self.client = None
        self._init_client()

    def _init_client(self):
        if self.api_key and self.api_key != "YOUR_GEMINI_API_KEY":
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Google Gen AI Client: {e}")
                self.client = None

    def is_configured(self) -> bool:
        return bool(self.client and self.api_key and self.api_key != "YOUR_GEMINI_API_KEY")

    def plan_automation(self, instruction: str, current_screen_info: Dict[str, Any], current_app: str) -> Optional[ActionPlan]:
        if not self.is_configured():
            logger.warning("Gemini API is not configured. Falling back to rule-based fallback planner.")
            return None

        prompt = f"""
You are an expert Android Phone Automation Agent.
Your task is to take a user instruction, analyze current screen state, and decompose the instruction into an ORDERED, SEQUENTIAL, VALIDATED plan of actions to execute on the Android device.

User Instruction: "{instruction}"
Current Foreground App: "{current_app}"
Current Screen Elements Summary:
{json.dumps(current_screen_info, indent=2)}

Common Android Package Names:
- YouTube: com.google.android.youtube
- Google Chrome: com.android.chrome
- Google Play Store: com.android.vending
- Settings: com.android.settings
- WhatsApp: com.whatsapp
- Messages: com.google.android.apps.messaging
- Camera: com.android.camera

Supported Action Types & Expected Fields:
1. OPEN_APP (package_name: string, app_name: string)
2. WAIT_FOR_APP (package_name: string, timeout: float)
3. WAIT_FOR_ELEMENT (text?: string, content_description?: string, resource_id?: string, timeout: float)
4. TAP_TEXT (text: string, fallback_text?: string, match_index?: int)
5. TAP_CONTENT_DESCRIPTION (content_description: string, fallback_content_description?: string, match_index?: int)
6. TAP_COORDINATES (x: int, y: int) - use ONLY when text/content description cannot be determined
7. TYPE_TEXT (text: string) - types into currently focused input
8. PRESS_ENTER - submits search or input field (sends KEYCODE_ENTER 66)
9. SWIPE (direction: "up" | "down" | "left" | "right")
10. PRESS_BACK - navigates back
11. PRESS_HOME - returns to home screen
12. WAIT (seconds: float) - explicit sleep
13. TAKE_SCREENSHOT
14. READ_SCREEN
15. ASK_CONFIRMATION (reason: string) - required for sensitive operations (financial, payments, deletion, permissions)

CRITICAL RULES FOR MULTI-STEP ACTIONS:
1. Break down long complex instructions into logical, sequential steps. Never skip intermediary steps (e.g. to search YouTube: open app -> wait for app -> tap search -> wait for input -> type search query -> press enter -> wait for results -> tap first result).
2. DO NOT assume UI appears instantaneously. Always insert WAIT_FOR_APP, WAIT_FOR_ELEMENT, or WAIT between navigation/open/search actions.
3. Use dynamic text or content_description instead of fixed coordinates whenever possible.
4. Total steps must not exceed {MAX_ACTION_STEPS}.

CRITICAL SAFETY RULE:
If the user's instruction involves sending real money/payments, sending a message/call, deleting items, altering system passwords, or granting security permissions, set "requires_confirmation": true and explain why in "confirmation_message".

You must respond ONLY with a valid JSON object matching this schema:
{{
  "task": "short summary of task",
  "actions": [
    {{
      "type": "OPEN_APP",
      "app_name": "YouTube",
      "package_name": "com.google.android.youtube"
    }},
    {{
      "type": "WAIT_FOR_APP",
      "package_name": "com.google.android.youtube",
      "timeout": 5.0
    }}
  ],
  "requires_confirmation": false,
  "confirmation_message": null
}}
"""
        # Model candidates to handle quota limits or specific model availability
        candidates = [self.model_name]
        for fallback in ["gemini-2.0-flash", "gemini-1.5-flash"]:
            if fallback not in candidates:
                candidates.append(fallback)

        for model in candidates:
            try:
                from google.genai import types
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                raw_text = response.text
                data = json.loads(raw_text)
                return ActionPlan.model_validate(data)
            except Exception as e:
                logger.warning(f"Gemini API attempt with model '{model}' failed: {e}")
                continue

        logger.error("All Gemini API model attempts failed. Falling back to rule-based planner.")
        return None
