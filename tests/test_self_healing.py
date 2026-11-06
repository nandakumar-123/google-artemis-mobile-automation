from unittest.mock import MagicMock
from app.adb_manager import ADBManager
from app.screen_reader import ScreenReader, UIElement
from app.verification import ActionVerifier
from app.device_controller import DeviceController
from app.schemas import ActionItem

def test_verification_successful_state_change():
    mock_adb = MagicMock(spec=ADBManager)
    mock_screen = MagicMock(spec=ScreenReader)
    
    # Pre-state: Home screen with few icons
    mock_adb.get_current_app.return_value = "com.google.android.apps.nexuslauncher"
    mock_screen.get_screen_summary.side_effect = [
        {"visible_texts": ["Phone", "Messages"], "interactive_elements": [{"clickable": True}, {"clickable": True}]},
        # Post-state: YouTube launched with new elements
        {"visible_texts": ["YouTube", "Search", "Home", "Subscriptions"], "interactive_elements": [{"clickable": True}] * 5}
    ]
    
    verifier = ActionVerifier(mock_adb, mock_screen)
    pre_state = verifier.capture_screen_fingerprint()
    
    # Test verified TAP_TEXT action
    mock_adb.get_current_app.return_value = "com.google.android.youtube"
    res = verifier.verify_action_result(
        action_type="TAP_TEXT",
        action_data={"text": "YouTube"},
        initial_app="com.google.android.apps.nexuslauncher",
        pre_state=pre_state
    )
    assert res["verified"] is True
    assert "Screen updated after tap" in res["details"]

def test_verification_failed_no_state_change():
    mock_adb = MagicMock(spec=ADBManager)
    mock_screen = MagicMock(spec=ScreenReader)
    
    # Frozen screen: exactly identical elements before and after
    mock_adb.get_current_app.return_value = "com.example.app"
    mock_screen.get_screen_summary.return_value = {
        "visible_texts": ["Button A", "Button B"],
        "interactive_elements": [{"clickable": True}, {"clickable": True}]
    }
    
    verifier = ActionVerifier(mock_adb, mock_screen)
    pre_state = verifier.capture_screen_fingerprint()
    
    res = verifier.verify_action_result(
        action_type="TAP_TEXT",
        action_data={"text": "Button A"},
        initial_app="com.example.app",
        pre_state=pre_state
    )
    assert res["verified"] is False
    assert "screen state did not change" in res["details"].lower()
    assert res["failure_reason"] is not None

def test_recovery_attempts_maximum_limit():
    controller = DeviceController()
    controller.adb = MagicMock(spec=ADBManager)
    controller.screen_reader = MagicMock(spec=ScreenReader)
    controller.verifier = MagicMock(spec=ActionVerifier)
    controller.gemini = MagicMock()

    controller.adb.check_connection_status.return_value = {"connected": True, "status": "Connected"}
    controller.adb.get_current_app.return_value = "com.example.app"
    controller.screen_reader.get_screen_summary.return_value = {"visible_texts": ["Submit"], "interactive_elements": []}
    controller.screen_reader.capture_screenshot.return_value = None

    # Executor always fails
    controller.executor.execute_action = MagicMock(return_value={"status": "failed", "message": "Element not found"})
    controller.verifier.capture_screen_fingerprint.return_value = {"foreground_app": "com.example.app", "visible_texts": [], "text_set": set(), "element_count": 0}
    controller.verifier.verify_action_result.return_value = {"verified": False, "failure_reason": "Element not found"}

    # Mock recovery returning corrected actions
    controller.gemini.plan_recovery_action.return_value = ActionItem(type="TAP_TEXT", text="Submit_Alt", reason="Alternative selector")

    actions = [ActionItem(type="TAP_TEXT", text="Submit", retry_count=2)]
    result = controller._run_action_sequence(task_id=999, instruction="tap submit", actions=actions)

    assert result["success"] is False
    executed = result["actions_executed"]
    assert len(executed) == 1
    # Recovery count must not exceed maximum of 2
    assert executed[0]["recovery_attempts"] == 2

def test_cancellation_during_execution():
    controller = DeviceController()
    controller.adb = MagicMock(spec=ADBManager)
    controller.screen_reader = MagicMock(spec=ScreenReader)
    controller.verifier = MagicMock(spec=ActionVerifier)
    
    controller.adb.check_connection_status.return_value = {"connected": True, "status": "Connected"}
    controller.adb.get_current_app.return_value = "com.example.app"
    controller.screen_reader.capture_screenshot.return_value = None
    controller.verifier.capture_screen_fingerprint.return_value = {"foreground_app": "com.example.app", "visible_texts": [], "text_set": set(), "element_count": 0}

    # Request stop before running
    controller.stop_execution()
    assert controller.executor.stop_requested is True

    actions = [
        ActionItem(type="OPEN_APP", package_name="com.android.settings"),
        ActionItem(type="TAP_TEXT", text="Display")
    ]
    result = controller._run_action_sequence(task_id=1000, instruction="open display settings", actions=actions)

    assert result["success"] is False
    assert "cancel" in result["message"].lower() or "stop" in result["message"].lower()
