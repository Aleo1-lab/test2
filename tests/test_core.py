import unittest
from unittest.mock import MagicMock, patch, ANY
import time

# Add project root to sys.path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external libraries before importing AppCore
# This ensures AppCore and its imports use these mocks from the start.

# Mock pynput
mock_pynput_keyboard = MagicMock()
mock_pynput_mouse = MagicMock()

# Configure pynput.keyboard.Key (as a mock object with attributes like 'esc', 'f12')
mock_key_obj = MagicMock()
mock_key_obj.esc = MagicMock(name='Key.esc')
mock_key_obj.f12 = MagicMock(name='Key.f12')
# Add other keys if AppCore specifically checks for them (e.g., F1, F5 if used as triggers in tests)
mock_key_obj.f1 = MagicMock(name='Key.f1')
mock_key_obj.f5 = MagicMock(name='Key.f5')
mock_pynput_keyboard.Key = mock_key_obj

# Configure pynput.keyboard.KeyCode (as a callable mock that returns instances)
# Each instance should have a 'char' attribute.
def mock_keycode_constructor(char):
    instance = MagicMock(name=f"KeyCode_{char}")
    instance.char = char
    return instance
mock_pynput_keyboard.KeyCode = MagicMock(side_effect=mock_keycode_constructor)
mock_pynput_keyboard.Listener = MagicMock(return_value=MagicMock(name='KeyboardListenerInstance'))


# Configure pynput.mouse.Button (as a mock object with attributes like 'left', 'right')
mock_button_obj = MagicMock()
mock_button_obj.left = MagicMock(name='Button.left')
mock_button_obj.right = MagicMock(name='Button.right')
# Add other buttons if needed
mock_pynput_mouse.Button = mock_button_obj
mock_pynput_mouse.Listener = MagicMock(return_value=MagicMock(name='MouseListenerInstance'))

# Apply mocks to sys.modules
sys.modules['pynput'] = MagicMock(keyboard=mock_pynput_keyboard, mouse=mock_pynput_mouse)
sys.modules['pynput.keyboard'] = mock_pynput_keyboard
sys.modules['pynput.mouse'] = mock_pynput_mouse


# Mock pyautogui
from collections import namedtuple
Point = namedtuple('Point', ['x', 'y'])
mock_pyautogui = MagicMock()
mock_pyautogui.PAUSE = 0
mock_pyautogui.FAILSAFE = False
mock_pyautogui.position = MagicMock(return_value=Point(0, 0))
mock_pyautogui.click = MagicMock()
sys.modules['pyautogui'] = mock_pyautogui


from core import AppCore, STATUS_IDLE, STATUS_ERROR, KEY_NOT_ASSIGNED, ASSIGN_KEY_PROMPT, COLOR_GREEN, COLOR_RED
from click_modes import ClickMode # Assuming ClickMode is imported in core or used for type hints

class TestAppCore(unittest.TestCase):

    @patch('core.AutoClickerUI') # Mock the UI class passed to AppCore
    @patch('core.get_click_mode') # Mock the factory function for click modes
    def setUp(self, mock_get_click_mode_factory, mock_auto_clicker_ui_class):
        # Reset mocks for pyautogui and pynput listeners before each test
        mock_pyautogui.reset_mock()
        mock_pyautogui.position.return_value = Point(0, 0) # Ensure default position

        mock_pynput_keyboard.Listener.reset_mock()
        mock_pynput_keyboard.Listener.return_value.start.reset_mock()
        mock_pynput_mouse.Listener.reset_mock()
        mock_pynput_mouse.Listener.return_value.start.reset_mock()


        # Mock the UI instance that AppCore will create and use
        self.mock_ui_instance = MagicMock()
        mock_auto_clicker_ui_class.return_value = self.mock_ui_instance

        # Mock the click mode instances that AppCore will get
        self.mock_left_click_mode_instance = MagicMock(spec=ClickMode, name="LeftClickModeInstance")
        self.mock_right_click_mode_instance = MagicMock(spec=ClickMode, name="RightClickModeInstance")

        # Configure the factory to return the appropriate mock instance based on mode name (or type)
        # AppCore initializes modes for 'left' and 'right' during its __init__ via on_mode_changed
        # For simplicity, assume 'Sabit' mode is default and used for both initially.
        def get_mode_side_effect(mode_name, app_core_ref):
            if app_core_ref.left_click_mode is None : # Rough way to distinguish calls during setup
                 # This is a bit fragile; depends on AppCore internal calls during init.
                 # A better way might be to check mode_name or have UI call on_mode_changed with specific types.
                 # For now, assume first call is for left, second for right if they are sequential.
                 # Or, more robustly, track calls if AppCore calls on_mode_changed with type.
                 # The current AppCore calls on_mode_changed from UI's _on_mode_change,
                 # which passes 'left' then 'right'. So this can be tied to call count or specific args.
                return self.mock_left_click_mode_instance
            return self.mock_right_click_mode_instance

        # More robust side effect for get_click_mode based on call order or specific needs
        # AppCore's __init__ doesn't directly call on_mode_changed.
        # The UI's __init__ calls _on_mode_change for 'left' and 'right', which calls core.on_mode_changed.
        # So, the mock_get_click_mode_factory will be called twice.
        mock_get_click_mode_factory.side_effect = [
            self.mock_left_click_mode_instance,  # First call (likely for 'left' via UI init)
            self.mock_right_click_mode_instance  # Second call (likely for 'right' via UI init)
        ]


        # Default settings from UI mock
        self.default_left_settings = {
            'mode': "Sabit", 'peak_cps': 10.0, 'timing_rand_ms': "10", 'jitter_px': "5",
        }
        self.default_right_settings = {
            'mode': "Sabit", 'peak_cps': 8.0, 'timing_rand_ms': "15", 'jitter_px': "3",
        }
        self.mock_ui_instance.get_current_settings.return_value = {
            'left': self.default_left_settings,
            'right': self.default_right_settings
        }

        self.app_core = AppCore()

    def test_initialization(self):
        self.assertIsNotNone(self.app_core.ui)
        self.assertIsNotNone(self.app_core.left_click_mode) # Check specific mode
        self.assertIsNotNone(self.app_core.right_click_mode)
        self.assertFalse(self.app_core.is_running)
        self.assertFalse(self.app_core.is_left_clicking)
        self.assertFalse(self.app_core.is_right_clicking)
        self.assertIsNone(self.app_core.left_trigger_input) # Specific trigger
        self.assertIsNone(self.app_core.right_trigger_input)

        # Check that listeners were started
        mock_pynput_keyboard.Listener.assert_called_once_with(on_press=self.app_core._on_key_press_event)
        mock_pynput_keyboard.Listener.return_value.start.assert_called_once()
        mock_pynput_mouse.Listener.assert_called_once_with(on_click=self.app_core._on_mouse_click_event)
        mock_pynput_mouse.Listener.return_value.start.assert_called_once()


    @patch('core.get_click_mode') # Patch the factory directly for this test
    def test_on_mode_changed(self, mock_get_click_mode_factory_local):
        # This method in AppCore is now more complex due to dual click types.
        # The mock_get_click_mode_factory is shared, so care is needed.

        # Test changing left click mode
        new_left_mode_mock = MagicMock(spec=ClickMode, name="NewLeftMode")
        # Configure the factory for this specific call
        mock_get_click_mode_factory_local.return_value = new_left_mode_mock

        self.app_core.on_mode_changed("Patlama", "left")
        mock_get_click_mode_factory_local.assert_called_with("Patlama", self.app_core)
        self.assertEqual(self.app_core.left_click_mode, new_left_mode_mock)
        new_left_mode_mock.reset.assert_called_once()
        # Ensure right_click_mode was not affected by this call (it should retain its instance from setUp)
        self.assertEqual(self.app_core.right_click_mode, self.mock_right_click_mode_instance)


        # Test changing right click mode
        new_right_mode_mock = MagicMock(spec=ClickMode, name="NewRightMode")
        mock_get_click_mode_factory_local.return_value = new_right_mode_mock # Reconfigure for next call
        new_right_mode_mock.reset_mock() # Clear reset calls from previous potential uses if any

        self.app_core.on_mode_changed("Dalgalı (Sinüs)", "right")
        mock_get_click_mode_factory_local.assert_called_with("Dalgalı (Sinüs)", self.app_core)
        self.assertEqual(self.app_core.right_click_mode, new_right_mode_mock)
        new_right_mode_mock.reset.assert_called_once()
        # Ensure left_click_mode was not affected by this call
        self.assertEqual(self.app_core.left_click_mode, new_left_mode_mock) # Should be the one set previously


    @patch('core.get_click_mode') # Patch within the test method
    def test_on_mode_changed_error_handling(self, mock_get_mode_factory_local):
        # Simulate error for 'left' click mode
        # Mock the fallback mode that AppCore tries to load
        fallback_mock = MagicMock(spec=ClickMode, name="FallbackMode")

        def get_mode_side_effect_for_error(mode_name, core_ref):
            if mode_name == "InvalidModeName":
                raise ValueError("Test Mode Load Error")
            elif mode_name == "Sabit": # Fallback mode name
                return fallback_mock
            return MagicMock(spec=ClickMode, name=f"OtherMode_{mode_name}")

        mock_get_mode_factory_local.side_effect = get_mode_side_effect_for_error

        self.app_core.on_mode_changed("InvalidModeName", "left")

        mock_get_mode_factory_local.assert_any_call("InvalidModeName", self.app_core)
        mock_get_mode_factory_local.assert_any_call("Sabit", self.app_core) # Fallback attempt
        self.assertEqual(self.app_core.left_click_mode, fallback_mock)
        fallback_mock.reset.assert_called_once()

    def test_validate_specific_params_valid(self):
        # Test for 'left' click type
        params = self.app_core._validate_specific_params(self.default_left_settings, "Sol Tık")
        self.assertIsNotNone(params)
        self.assertEqual(params['peak_cps'], self.default_left_settings['peak_cps'])

        # Test for 'right' click type
        params_right = self.app_core._validate_specific_params(self.default_right_settings, "Sağ Tık")
        self.assertIsNotNone(params_right)
        self.assertEqual(params_right['peak_cps'], self.default_right_settings['peak_cps'])


    def test_validate_specific_params_invalid_cps(self):
        invalid_settings = {**self.default_left_settings, 'peak_cps': -5.0} # Invalid CPS
        params = self.app_core._validate_specific_params(invalid_settings, "Sol Tık")
        self.assertIsNone(params)
        # AppCore's _validate_specific_params calls ui.show_error and ui.update_status_display
        self.mock_ui_instance.update_status_display.assert_called_with(STATUS_ERROR, COLOR_RED, self.app_core.is_running)
        self.mock_ui_instance.show_error.assert_called_once_with("Sol Tık Geçersiz Girdi", "Lütfen ayarları kontrol edin.\nHata: Sol Tık CPS pozitif olmalı.")


    def test_validate_and_store_params(self):
        # Test for 'left'
        # mock_left_click_mode_instance was reset once in setUp.
        # _validate_and_store_params calls reset again.
        self.mock_left_click_mode_instance.reset_mock() # Clear prior reset calls for this test part
        result_left = self.app_core._validate_and_store_params('left')
        self.assertTrue(result_left)
        self.assertIn('left', self.app_core.active_click_params)
        self.assertEqual(self.app_core.active_click_params['left']['peak_cps'], self.default_left_settings['peak_cps'])
        self.mock_left_click_mode_instance.reset.assert_called_once()


        # Test for 'right'
        self.mock_right_click_mode_instance.reset_mock() # Clear prior reset calls for this test part
        result_right = self.app_core._validate_and_store_params('right')
        self.assertTrue(result_right)
        self.assertIn('right', self.app_core.active_click_params)
        self.assertEqual(self.app_core.active_click_params['right']['peak_cps'], self.default_right_settings['peak_cps'])
        self.mock_right_click_mode_instance.reset.assert_called_once()


    def test_toggle_left_click_start_stop(self):
        # Start left click
        self.app_core.left_trigger_input = mock_pynput_keyboard.Key.f1 # Assign a trigger
        # Reset call count for left_click_mode.reset()
        # It's called once in setUp, once in _validate_and_store_params (if successful), once in toggle_left_click.
        self.mock_left_click_mode_instance.reset_mock()

        with patch.object(self.app_core, '_validate_and_store_params', return_value=True) as mock_validate, \
             patch.object(self.app_core, '_manage_click_thread') as mock_manage_thread:

            self.app_core.toggle_left_click()

            self.assertTrue(self.app_core.is_left_clicking)
            self.assertTrue(self.app_core.is_running) # is_running should be true
            mock_validate.assert_called_once_with('left')
            self.mock_left_click_mode_instance.reset.assert_called_once() # Called by toggle_left_click itself
            mock_manage_thread.assert_called_once()
            self.mock_ui_instance.update_status_display.assert_called_with("Durum: SOL TIK AKTİF", COLOR_GREEN, True)

        # Stop left click
        with patch.object(self.app_core, '_manage_click_thread') as mock_manage_thread: # New mock for this scope
            self.app_core.toggle_left_click() # Call again to stop
            self.assertFalse(self.app_core.is_left_clicking)
            # is_running depends on whether right click is also active, assume not for this test
            self.assertFalse(self.app_core.is_running)
            mock_manage_thread.assert_called_once() # Thread management should be called
            self.mock_ui_instance.update_status_display.assert_called_with(STATUS_IDLE, ANY, False)


    def test_toggle_right_click_start_stop(self):
        self.app_core.right_trigger_input = mock_pynput_keyboard.Key.f5
        self.mock_right_click_mode_instance.reset_mock()

        with patch.object(self.app_core, '_validate_and_store_params', return_value=True) as mock_validate, \
             patch.object(self.app_core, '_manage_click_thread') as mock_manage_thread:

            self.app_core.toggle_right_click()
            self.assertTrue(self.app_core.is_right_clicking)
            self.assertTrue(self.app_core.is_running)
            mock_validate.assert_called_once_with('right')
            self.mock_right_click_mode_instance.reset.assert_called_once()
            mock_manage_thread.assert_called_once()
            self.mock_ui_instance.update_status_display.assert_called_with("Durum: SAĞ TIK AKTİF", COLOR_GREEN, True)

        with patch.object(self.app_core, '_manage_click_thread') as mock_manage_thread:
            self.app_core.toggle_right_click()
            self.assertFalse(self.app_core.is_right_clicking)
            self.assertFalse(self.app_core.is_running)
            mock_manage_thread.assert_called_once()
            self.mock_ui_instance.update_status_display.assert_called_with(STATUS_IDLE, ANY, False)


    def test_toggle_both_clicks_then_stop_one(self):
        self.app_core.left_trigger_input = mock_pynput_keyboard.Key.f1
        self.app_core.right_trigger_input = mock_pynput_keyboard.Key.f5

        # Reset mode reset counters
        self.mock_left_click_mode_instance.reset_mock()
        self.mock_right_click_mode_instance.reset_mock()

        with patch.object(self.app_core, '_validate_and_store_params', return_value=True) as mock_validate, \
             patch.object(self.app_core, '_manage_click_thread') as mock_manage_thread:

            self.app_core.toggle_left_click() # Start left
            mock_validate.assert_called_with('left')
            self.mock_left_click_mode_instance.reset.assert_called_once()
            mock_manage_thread.assert_called_once() # Thread started

            mock_validate.reset_mock() # Reset for next call
            self.mock_right_click_mode_instance.reset_mock() # Reset for next call
            mock_manage_thread.reset_mock()

            self.app_core.toggle_right_click() # Start right
            mock_validate.assert_called_with('right')
            self.mock_right_click_mode_instance.reset.assert_called_once()
            mock_manage_thread.assert_called_once() # Thread potentially re-managed (or checked)

            self.assertTrue(self.app_core.is_left_clicking)
            self.assertTrue(self.app_core.is_right_clicking)
            self.assertTrue(self.app_core.is_running)
            self.mock_ui_instance.update_status_display.assert_called_with("Durum: SOL & SAĞ TIK AKTİF", COLOR_GREEN, True)

            mock_manage_thread.reset_mock()
            self.app_core.toggle_left_click() # Stop left

            self.assertFalse(self.app_core.is_left_clicking)
            self.assertTrue(self.app_core.is_right_clicking) # Right should still be active
            self.assertTrue(self.app_core.is_running) # Overall still running
            mock_manage_thread.assert_called_once() # Thread managed
            self.mock_ui_instance.update_status_display.assert_called_with("Durum: SAĞ TIK AKTİF", COLOR_GREEN, True)


    @patch('core.threading.Thread')
    def test_manage_click_thread_starts_thread(self, mock_thread_class):
        mock_thread_instance = MagicMock(name="ClickThreadInstance")
        mock_thread_class.return_value = mock_thread_instance

        self.app_core.is_left_clicking = True # Simulate one click type active
        self.app_core.click_thread = None # Ensure no existing thread
        self.app_core._manage_click_thread()

        mock_thread_class.assert_called_once_with(target=self.app_core._click_loop, daemon=True)
        mock_thread_instance.start.assert_called_once()
        self.assertEqual(self.app_core.click_thread, mock_thread_instance)

    def test_manage_click_thread_no_action_if_thread_already_running_for_active_clicks(self):
        # Simulate thread already running and clicks are active
        self.app_core.click_thread = MagicMock(is_alive=lambda: True)
        self.app_core.is_left_clicking = True
        with patch('core.threading.Thread') as mock_thread_class: # Ensure new thread not started
            self.app_core._manage_click_thread()
            mock_thread_class.assert_not_called()


    def test_manage_click_thread_signals_stop_implicitly(self):
        # Thread stops when is_left_clicking and is_right_clicking are both false
        self.app_core.click_thread = MagicMock(is_alive=lambda: True) # Mock existing thread
        self.app_core.is_left_clicking = False
        self.app_core.is_right_clicking = False

        self.app_core._manage_click_thread()
        # No direct stop call, loop condition in thread handles termination.
        # _manage_click_thread doesn't directly change is_running, _update_global_state_and_ui does.
        # This test primarily checks that a new thread isn't started if clicks are off.
        # The effect on self.is_running is tested via toggle methods which call _update_global_state_and_ui.
        self.assertIsNotNone(self.app_core.click_thread) # Thread object itself is not cleared here


    def test_set_assign_mode_left_and_right(self):
        # Assign for left
        self.app_core.set_assign_mode('left')
        self.assertTrue(self.app_core.assigning_for_left)
        self.assertFalse(self.app_core.assigning_for_right)
        self.mock_ui_instance.update_trigger_key_display.assert_any_call(ASSIGN_KEY_PROMPT, False, 'left')
        # It also updates the *other* trigger label to normal if it was assigning
        self.mock_ui_instance.update_trigger_key_display.assert_any_call(KEY_NOT_ASSIGNED, False, 'right') # Assuming right trigger is initially None

        # Assign for right
        self.app_core.set_assign_mode('right')
        self.assertFalse(self.app_core.assigning_for_left)
        self.assertTrue(self.app_core.assigning_for_right)
        self.mock_ui_instance.update_trigger_key_display.assert_any_call(ASSIGN_KEY_PROMPT, False, 'right')
        self.mock_ui_instance.update_trigger_key_display.assert_any_call(KEY_NOT_ASSIGNED, False, 'left') # Assuming left trigger is now None or reset


    def test_assign_input_keyboard_and_mouse(self):
        # Assign left keyboard key
        self.app_core.set_assign_mode('left')
        test_key = mock_pynput_keyboard.KeyCode(char='a') # Mock KeyCode('a')
        self.app_core._assign_input(test_key)
        self.assertFalse(self.app_core.assigning_for_left)
        self.assertEqual(self.app_core.left_trigger_input, test_key)
        self.mock_ui_instance.update_trigger_key_display.assert_called_with('A', True, 'left')

        # Assign right mouse button
        self.app_core.set_assign_mode('right')
        test_mouse_button = mock_pynput_mouse.Button.right # Mock Button.right
        self.app_core._assign_input(test_mouse_button)
        self.assertFalse(self.app_core.assigning_for_right)
        self.assertEqual(self.app_core.right_trigger_input, test_mouse_button)
        self.mock_ui_instance.update_trigger_key_display.assert_called_with('MOUSE_RIGHT', True, 'right')

    def test_assign_input_cancel_with_esc(self):
        self.app_core.set_assign_mode('left')
        self.app_core.left_trigger_input = mock_pynput_keyboard.Key.f1 # Pre-existing mock key

        self.app_core._assign_input(mock_pynput_keyboard.Key.esc) # Mock Key.esc
        self.assertFalse(self.app_core.assigning_for_left)
        self.assertEqual(self.app_core.left_trigger_input, mock_pynput_keyboard.Key.f1) # Unchanged
        # format_input_name will be called for Key.f1
        self.mock_ui_instance.update_trigger_key_display.assert_called_with('F1', True, 'left')


    @patch('core.sys.exit')
    def test_emergency_shutdown(self, mock_sys_exit):
        self.app_core.is_running = True # Simulate running state
        self.app_core.emergency_shutdown()
        self.assertFalse(self.app_core.is_running) # is_running should be set to False
        self.assertFalse(self.app_core.is_left_clicking) # Individual flags also false
        self.assertFalse(self.app_core.is_right_clicking)
        if self.app_core.ui: # UI might be None if tests run headless without full Tk
            self.mock_ui_instance.destroy.assert_called_once()
        mock_sys_exit.assert_called_once()


    def test_on_key_press_event_f12_shutdown(self):
        with patch.object(self.app_core, 'emergency_shutdown') as mock_shutdown:
            self.app_core._on_key_press_event(mock_pynput_keyboard.Key.f12) # Use mock Key.f12
            self.mock_ui_instance.after.assert_called_once_with(0, mock_shutdown)

    def test_on_key_press_event_triggers_left_right(self):
        # Setup left trigger (keyboard)
        left_trigger_key = mock_pynput_keyboard.KeyCode(char='q') # Mock KeyCode('q')
        self.app_core.left_trigger_input = left_trigger_key
        # Setup right trigger (keyboard)
        right_kb_trigger = mock_pynput_keyboard.KeyCode(char='w') # Mock KeyCode('w')
        self.app_core.right_trigger_input = right_kb_trigger

        # Test left trigger
        with patch.object(self.app_core, 'toggle_left_click') as mock_toggle_left:
            self.app_core._on_key_press_event(left_trigger_key)
            self.mock_ui_instance.after.assert_called_with(0, mock_toggle_left) # Schedule toggle

        # Test right trigger
        with patch.object(self.app_core, 'toggle_right_click') as mock_toggle_right:
            self.app_core._on_key_press_event(right_kb_trigger)
            self.mock_ui_instance.after.assert_called_with(0, mock_toggle_right) # Schedule toggle


    def test_on_mouse_click_event_triggers_left_right(self):
        # Setup left mouse trigger
        left_mouse_trigger = mock_pynput_mouse.Button.left # Mock Button.left
        self.app_core.left_trigger_input = left_mouse_trigger
        # Setup right mouse trigger
        right_mouse_trigger = mock_pynput_mouse.Button.right # Mock Button.right
        self.app_core.right_trigger_input = right_mouse_trigger

        # Test left trigger
        with patch.object(self.app_core, 'toggle_left_click') as mock_toggle_left:
            # Args for _on_mouse_click_event: x, y, button, pressed
            self.app_core._on_mouse_click_event(0, 0, left_mouse_trigger, True)
            self.mock_ui_instance.after.assert_called_with(0, mock_toggle_left)

        # Test right trigger
        with patch.object(self.app_core, 'toggle_right_click') as mock_toggle_right:
            self.app_core._on_mouse_click_event(0, 0, right_mouse_trigger, True)
            self.mock_ui_instance.after.assert_called_with(0, mock_toggle_right)

        # Test event ignored if not pressed
        self.mock_ui_instance.after.reset_mock() # Reset call count for mock_ui_instance.after
        self.app_core._on_mouse_click_event(0,0, right_mouse_trigger, False) # Not pressed
        self.mock_ui_instance.after.assert_not_called() # Should not schedule toggle


    def test_on_event_assigning_input(self):
        key_to_assign = mock_pynput_keyboard.KeyCode(char='z') # Mock KeyCode('z')
        self.app_core.set_assign_mode('left') # Enter assignment mode for left click

        with patch.object(self.app_core, '_assign_input') as mock_assign_key: # Renamed for clarity
            self.app_core._on_key_press_event(key_to_assign)
            self.mock_ui_instance.after.assert_called_with(0, mock_assign_key, key_to_assign)

        mouse_button_to_assign = mock_pynput_mouse.Button.left # Mock Button.left (can be any button)
        self.app_core.set_assign_mode('right') # Enter assignment mode for right click
        with patch.object(self.app_core, '_assign_input') as mock_assign_mouse:
            self.app_core._on_mouse_click_event(0,0, mouse_button_to_assign, True) # pressed=True
            self.mock_ui_instance.after.assert_called_with(0, mock_assign_mouse, mouse_button_to_assign)


    # --- _click_loop Tests ---
    # These are more complex and test the core clicking logic with dual modes.

    @patch('core.time.sleep') # Mock time.sleep
    @patch('core.time.time')  # Mock time.time for precise control
    @patch('core.random.uniform', return_value=0.0) # No random delay component
    def test_click_loop_left_click_only(self, mock_random_uniform, mock_time, mock_sleep):
        # Configure AppCore for left click only
        self.app_core.is_left_clicking = True
        self.app_core.is_right_clicking = False
        self.app_core.is_running = True # Global flag, should be true if any click is active
        self.app_core.active_click_params['left'] = {
            'peak_cps': 10.0, 'timing_rand_ms': 0, 'jitter_px': 0, 'mode': 'Sabit' # Ensure mode is there
        }
        self.app_core.left_click_mode = self.mock_left_click_mode_instance # Ensure mode instance is set
        self.mock_left_click_mode_instance.get_next_action.return_value = (10.0, 0, 0, 1.0) # CPS, JitterX, JitterY, Multiplier

        # Simulate time progression for one click
        # time() will be called at start of loop, then for current_time inside, then for sleep duration calculation
        # Let one cycle take 0.1s (10 CPS)
        # We need a list of time values for the side_effect of time.time()
        # Loop start, initial next_click_due_time, current_time for click, time for next_due calculation, time for sleep
        time_sequence = [1000.0, 1000.001, 1000.002, 1000.102, 1000.103] # Example sequence
        mock_time.side_effect = time_sequence

        # Allow loop to run for one click, then stop
        def get_next_action_side_effect_left(*args, **kwargs):
            # After this action, signal to stop the main loop for the test
            # This is done by setting the click type's flag to False
            self.app_core.is_left_clicking = False
            return (10.0, 0, 0, 1.0)
        self.mock_left_click_mode_instance.get_next_action.side_effect = get_next_action_side_effect_left

        self.app_core._click_loop()

        self.mock_left_click_mode_instance.get_next_action.assert_called_once()
        mock_pyautogui.click.assert_called_once_with(x=ANY, y=ANY, button='left')
        self.assertEqual(self.app_core.click_count, 1)
        self.mock_ui_instance.after.assert_any_call(0, self.mock_ui_instance.update_realtime_cps, 10.0, "Sol")
        self.mock_ui_instance.after.assert_any_call(0, self.mock_ui_instance.update_click_count, 1)

        # Check that sleep was called (it will be called with a small value if a click happened)
        mock_sleep.assert_called_with(0.001) # Short sleep after a click
        # is_running should be false because is_left_clicking became false and is_right_clicking was already false
        self.assertFalse(self.app_core.is_running)
        # _handle_thread_completion and _update_global_state_and_ui should be called via ui.after
        self.mock_ui_instance.after.assert_any_call(0, self.app_core._update_global_state_and_ui)
        self.mock_ui_instance.after.assert_any_call(0, self.app_core._handle_thread_completion)


    @patch('core.time.sleep')
    @patch('core.time.time')
    @patch('core.random.uniform', return_value=0.0)
    def test_click_loop_both_clicks_alternating_ish(self, mock_random_uniform, mock_time_func, mock_sleep_func):
        self.app_core.is_left_clicking = True
        self.app_core.is_right_clicking = True
        self.app_core.is_running = True
        self.app_core.active_click_params['left'] = {'peak_cps': 10.0, 'timing_rand_ms': 0, 'jitter_px': 0, 'mode': 'Sabit'} # 0.1s delay
        self.app_core.active_click_params['right'] = {'peak_cps': 5.0, 'timing_rand_ms': 0, 'jitter_px': 0, 'mode': 'Sabit'}  # 0.2s delay
        self.app_core.left_click_mode = self.mock_left_click_mode_instance
        self.app_core.right_click_mode = self.mock_right_click_mode_instance

        self.mock_left_click_mode_instance.get_next_action.return_value = (10.0, 0, 0, 1.0)
        self.mock_right_click_mode_instance.get_next_action.return_value = (5.0, 0, 0, 1.0)

        # Simulate time:
        # t=0.0: Loop starts. Both clicks due. Left clicks. next_left_due = 0.1. Right clicks. next_right_due = 0.2
        # t=0.1: Left clicks. next_left_due = 0.2. Right is still at next_right_due = 0.2
        # t=0.2: Left clicks. next_left_due = 0.3. Right clicks. next_right_due = 0.4
        time_values = [
            0.0,  # Initial time for loop + next_left_click_due_time + next_right_click_due_time
            0.001, # current_time for left click
            0.002, # current_time for right click
            0.1,   # current_time for next left click
            0.101, # current_time for potential right click (not due yet)
            0.2,   # current_time for next left click AND next right click
            0.201, # current_time for left
            0.202, # current_time for right
            0.3    # current_time for next left click
        ]
        mock_time_func.side_effect = time_values

        total_clicks_made = 0
        max_total_clicks_for_test = 4 # Stop after 4 clicks (e.g. 2 left, 2 right or similar)

        def side_effect_click_action_left(*args, **kwargs):
            nonlocal total_clicks_made
            total_clicks_made += 1
            if total_clicks_made >= max_total_clicks_for_test:
                self.app_core.is_left_clicking = False
                self.app_core.is_right_clicking = False # Stop all
            return (10.0, 0, 0, 1.0)

        def side_effect_click_action_right(*args, **kwargs):
            nonlocal total_clicks_made
            total_clicks_made += 1
            if total_clicks_made >= max_total_clicks_for_test:
                self.app_core.is_left_clicking = False
                self.app_core.is_right_clicking = False # Stop all
            return (5.0, 0, 0, 1.0)

        self.mock_left_click_mode_instance.get_next_action.side_effect = side_effect_click_action_left
        self.mock_right_click_mode_instance.get_next_action.side_effect = side_effect_click_action_right

        self.app_core._click_loop()

        # Check number of pyautogui clicks
        # Example: t=0 (L,R), t=0.1 (L), t=0.2 (L,R) -> L:3, R:2. Total: 5
        # If max_total_clicks_for_test = 4, then perhaps 2 Left, 2 Right.
        # This depends heavily on the exact timing simulation.
        self.assertLessEqual(mock_pyautogui.click.call_count, max_total_clicks_for_test)
        self.assertFalse(self.app_core.is_running) # Loop should terminate


    def test_click_loop_one_mode_signals_stop(self):
        # Left click runs normally, Right click mode returns 0 CPS after first click
        self.app_core.is_left_clicking = True
        self.app_core.is_right_clicking = True
        self.app_core.is_running = True
        self.app_core.active_click_params['left'] = {'peak_cps': 10.0, 'timing_rand_ms': 0, 'jitter_px': 0, 'mode': 'Sabit'}
        self.app_core.active_click_params['right'] = {'peak_cps': 5.0, 'timing_rand_ms': 0, 'jitter_px': 0, 'mode': 'Sabit'}
        self.app_core.left_click_mode = self.mock_left_click_mode_instance
        self.app_core.right_click_mode = self.mock_right_click_mode_instance

        self.mock_left_click_mode_instance.get_next_action.return_value = (10.0, 0, 0, 1.0)

        right_mode_call_count = 0
        def right_mode_action_signals_stop(*args, **kwargs):
            nonlocal right_mode_call_count
            right_mode_call_count += 1
            if right_mode_call_count > 1: # After the first successful click
                return (0, 0, 0, 1.0) # Signal stop for right click
            return (5.0, 0, 0, 1.0) # First click is normal
        self.mock_right_click_mode_instance.get_next_action.side_effect = right_mode_action_signals_stop

        # Mock time.sleep and time.time to run the loop for a few iterations
        time_seq_one_stop = [0.0, 0.001, 0.002, 0.1, 0.101, 0.2, 0.201, 0.202, 0.3, 0.301, 0.4, 0.401]
        with patch('core.time.sleep'), patch('core.time.time', side_effect=time_seq_one_stop):

            left_click_stop_counter = 0
            def left_mode_eventually_stops(*args, **kwargs):
                nonlocal left_click_stop_counter
                left_click_stop_counter +=1
                if left_click_stop_counter > 3: # Let left click a few times
                    self.app_core.is_left_clicking = False
                return (10.0,0,0,1.0)
            self.mock_left_click_mode_instance.get_next_action.side_effect = left_mode_eventually_stops

            self.app_core._click_loop()

        self.assertFalse(self.app_core.is_right_clicking) # Right click should have stopped itself
        self.assertFalse(self.app_core.is_left_clicking) # Left click also stopped by test condition
        self.assertFalse(self.app_core.is_running)
        self.assertEqual(right_mode_call_count, 2) # Called once normally, once to signal stop (0 CPS)
        self.assertGreaterEqual(self.mock_left_click_mode_instance.get_next_action.call_count, 1)


    def test_stop_clicking_after_current_cycle_flag(self):
        self.app_core.is_left_clicking = True
        self.app_core.is_running = True # Pre-condition: clicking is active
        self.app_core.active_click_params['left'] = {'peak_cps': 10.0, 'timing_rand_ms': 0, 'jitter_px': 0, 'mode': 'Sabit'}
        self.app_core.left_click_mode = self.mock_left_click_mode_instance
        self.mock_left_click_mode_instance.get_next_action.return_value = (10.0,0,0,1.0) # Mode would normally click

        self.app_core.stop_clicking_after_current_cycle() # Set the flag

        with patch('core.time.sleep'), patch('core.time.time', return_value=0.0): # Time doesn't need to advance
            self.app_core._click_loop()

        # Loop should exit immediately due to the flag, without performing clicks
        self.mock_left_click_mode_instance.get_next_action.assert_not_called()
        mock_pyautogui.click.assert_not_called()
        # The flag _stop_requested_after_cycle causes is_left_clicking and is_right_clicking to become false.
        # Then, is_running becomes false.
        self.assertFalse(self.app_core.is_left_clicking)
        self.assertFalse(self.app_core.is_right_clicking)
        self.assertFalse(self.app_core.is_running)


if __name__ == '__main__':
    unittest.main()
