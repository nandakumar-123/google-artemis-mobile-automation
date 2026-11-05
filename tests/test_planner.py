from app.gemini_service import GeminiService
from app.action_planner import ActionPlanner

def test_planner_youtube():
    gemini = GeminiService()
    planner = ActionPlanner(gemini)
    plan = planner.plan("Open YouTube and search for Python tutorials", {}, "com.android.launcher")
    assert plan is not None
    assert len(plan.actions) > 0
    types = [a.type for a in plan.actions]
    assert "OPEN_APP" in types
    assert "TYPE_TEXT" in types

def test_planner_safety_confirmation():
    gemini = GeminiService()
    planner = ActionPlanner(gemini)
    plan = planner.plan("Send money using UPI payment", {}, "com.android.launcher")
    assert plan.requires_confirmation is True
    assert len(plan.actions) > 0
    assert plan.actions[0].type == "ASK_CONFIRMATION"

def test_planner_navigation():
    gemini = GeminiService()
    planner = ActionPlanner(gemini)
    plan = planner.plan("Go back to the previous screen", {}, "com.android.settings")
    assert plan.actions[0].type == "PRESS_BACK"

