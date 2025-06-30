import unittest
from unittest.mock import MagicMock, patch, ANY
import time

# Add project root to sys.path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the entire pynput package and its submodules used by core
# This must be done BEFORE core and its dependencies are imported.
mock_pynput = MagicMock()
mock_pynput.keyboard = MagicMock()
# Define specific attributes that might be accessed directly like Key.esc
# The mock for 'Key' itself. Individual keys like 'esc', 'f1' are attributes of this mock.
mock_key_obj = MagicMock(spec=['esc', 'f1', 'f5', 'f12'])

# Configure each special key mock correctly
mock_esc_key = MagicMock(spec_set=['name', 'char'])
mock_esc_key.name = 'esc'; mock_esc_key.char = None
mock_key_obj.esc = mock_esc_key

mock_f1_key = MagicMock(spec_set=['name', 'char'])
mock_f1_key.name = 'f1'; mock_f1_key.char = None
mock_key_obj.f1 = mock_f1_key

mock_f5_key = MagicMock(spec_set=['name', 'char'])
mock_f5_key.name = 'f5'; mock_f5_key.char = None
mock_key_obj.f5 = mock_f5_key

mock_f12_key = MagicMock(spec_set=['name', 'char'])
mock_f12_key.name = 'f12'; mock_f12_key.char = None
mock_key_obj.f12 = mock_f12_key

mock_pynput.keyboard.Key = mock_key_obj

# Mock for KeyCode class (used for character keys)
# When pynput.keyboard.KeyCode(char='a') is called, it should return a mock with a .char attribute.
def keycode_side_effect(char):
    m = MagicMock(spec_set=['char', 'name']) # name might not be present on real KeyCode
    m.char = char
    m.name = None # Typically None for char keys
    return m
mock_pynput.keyboard.KeyCode = MagicMock(side_effect=keycode_side_effect)

mock_pynput.keyboard.Listener = MagicMock(return_value=MagicMock(name='Listener_instance'))
sys.modules['pynput'] = mock_pynput
sys.modules['pynput.keyboard'] = mock_pynput.keyboard
# The mock for KeyCode needs to be more specific for test_assign_key_set
# It's better to configure the return_value of mock_pynput.keyboard.KeyCode directly in the test
# or ensure its side_effect correctly simulates KeyCode(char='x') behavior.
# For now, the above side_effect for KeyCode should work for format_key_name.

# Mock pyautogui
from collections import namedtuple
Point = namedtuple('Point', ['x', 'y'])

mock_pyautogui_module = MagicMock() # Use a different name to avoid conflict with the variable in test methods
mock_pyautogui_module.PAUSE = 0
mock_pyautogui_module.FAILSAFE = False
# Default position mock returns a Point object, individual tests can override this if needed for specific coords
mock_pyautogui_module.position = MagicMock(return_value=Point(0,0))
mock_pyautogui_module.click = MagicMock()
sys.modules['pyautogui'] = mock_pyautogui_module


from core import AppCore, STATUS_IDLE, STATUS_RUNNING, STATUS_ERROR, KEY_NOT_ASSIGNED, ASSIGN_KEY_PROMPT
from click_modes import ClickMode

class TestAppCore(unittest.TestCase):

    @patch('core.AutoClickerUI')
    @patch('core.get_click_mode')
    def setUp(self, mock_get_click_mode, mock_auto_clicker_ui):
        global mock_pyautogui_module # Allow access to the module-level mock for resetting
        mock_pyautogui_module.reset_mock() # Corrected: Use mock_pyautogui_module
        mock_pyautogui_module.position.return_value = (0,0) # Reset position mock

        # Reset pynput listener mock
        if 'mock_pynput' in globals():
            global mock_pynput
            mock_pynput.keyboard.Listener.reset_mock()
            mock_pynput.keyboard.Listener.return_value.start.reset_mock()

        # Default side_effect for perf_counter if not overridden by a specific test
        self._test_core_fake_time = 0
        def default_perf_counter_side_effect():
            self._test_core_fake_time += 0.0001 # Small increment
            return self._test_core_fake_time

        # If core.time.perf_counter is patched at class/module level for all tests:
        # This requires core.time.perf_counter to be accessible as a mock object here.
        # If @patch is on methods, then it's passed to the method.
        # For now, individual tests patch it. This default won't apply unless we patch at class level.

        self.mock_ui_instance = MagicMock()
        mock_auto_clicker_ui.return_value = self.mock_ui_instance

        self.mock_click_mode_instance = MagicMock(spec=ClickMode)
        mock_get_click_mode.return_value = self.mock_click_mode_instance

        # Mock UI elements that core interacts with for settings
        # Ensure these mocks are fresh or correctly configured for each test.
        # Accessing .get on a MagicMock creates a new MagicMock if not already defined.
        # So, re-assigning .return_value is fine.
        self.mock_ui_instance.cps_mode_var.get.return_value = "Sabit"
        self.mock_ui_instance.get_current_settings.return_value = {
            'peak_cps': 10.0, 'timing_rand_ms': "10", 'jitter_px': "5",
            'mouse_button_pref': "Sol Tık", 'mode': "Sabit"
        }

        self.app_core = AppCore()

        # Ensure initial mode is set up
        mock_get_click_mode.assert_called_with("Sabit", self.app_core)
        self.mock_click_mode_instance.reset.assert_called_once()

        # Erroneous reset lines removed from here:
        # mock_pyautogui.reset_mock()
        # mock_keyboard.Listener.reset_mock()


    def test_initialization(self):
        self.assertIsNotNone(self.app_core.ui)
        self.assertIsNotNone(self.app_core.current_click_mode)
        self.assertFalse(self.app_core.is_running)
        self.assertIsNone(self.app_core.trigger_key)
        mock_pynput.keyboard.Listener.assert_called_once_with(on_press=self.app_core._on_key_press)
        mock_pynput.keyboard.Listener.return_value.start.assert_called_once()

    def test_on_mode_changed(self):
        new_mock_mode = MagicMock(spec=ClickMode)
        with patch('core.get_click_mode', return_value=new_mock_mode) as mock_factory:
            self.app_core.on_mode_changed("Patlama")
            mock_factory.assert_called_once_with("Patlama", self.app_core)
            self.assertEqual(self.app_core.current_click_mode, new_mock_mode)
            new_mock_mode.reset.assert_called_once()

    @patch('core.get_click_mode')
    def test_on_mode_changed_error(self, mock_get_click_mode_error):
        mock_get_click_mode_error.side_effect = ValueError("Test error")

        # Mock the fallback mode creation
        fallback_mock_mode = MagicMock(spec=ClickMode)

        # Need to make get_click_mode return the fallback mode on the second call
        def side_effect_func(mode_name, core_ref):
            if mode_name == "InvalidMode":
                raise ValueError("Test error")
            elif mode_name == "Sabit": # Fallback mode
                return fallback_mock_mode
            return MagicMock()

        mock_get_click_mode_error.side_effect = side_effect_func

        self.app_core.on_mode_changed("InvalidMode")

        self.mock_ui_instance.show_error.assert_called_once_with("Mod Hatası", "Test error")
        self.mock_ui_instance.mode_combo.set.assert_called_once_with("Sabit")
        self.assertEqual(self.app_core.current_click_mode, fallback_mock_mode)
        fallback_mock_mode.reset.assert_called_once()


    def test_get_validated_params_valid(self):
        params = self.app_core._get_validated_params()
        self.assertIsNotNone(params)
        self.assertEqual(params['peak_cps'], 10.0)

    def test_get_validated_params_invalid_cps(self):
        self.mock_ui_instance.get_current_settings.return_value['peak_cps'] = -5.0
        params = self.app_core._get_validated_params()
        self.assertIsNone(params)
        self.mock_ui_instance.update_status_display.assert_called_with(STATUS_ERROR, ANY, self.app_core.is_running)
        self.mock_ui_instance.show_error.assert_called_once()

    def test_get_validated_params_patlama_mode(self):
        self.mock_ui_instance.get_current_settings.return_value = {
            'peak_cps': 10.0, 'timing_rand_ms': "10", 'jitter_px': "5",
            'mouse_button_pref': "Sol Tık", 'mode': "Patlama", 'burst_duration': "5.0"
        }
        params = self.app_core._get_validated_params()
        self.assertIsNotNone(params)
        self.assertEqual(params['burst_duration'], 5.0)

    def test_get_validated_params_random_aralik_mode(self):
        self.mock_ui_instance.get_current_settings.return_value = {
            'peak_cps': 10.0, 'timing_rand_ms': "10", 'jitter_px': "5",
            'mouse_button_pref': "Sol Tık", 'mode': "Rastgele Aralık",
            'min_cps_random': "3.0", 'max_cps_random': "8.0"
        }
        params = self.app_core._get_validated_params()
        self.assertIsNotNone(params)
        self.assertEqual(params['min_cps_random'], 3.0)
        self.assertEqual(params['max_cps_random'], 8.0)

        # Test invalid: min > max
        self.mock_ui_instance.get_current_settings.return_value['min_cps_random'] = "10.0"
        params_invalid = self.app_core._get_validated_params()
        self.assertIsNone(params_invalid)
        self.mock_ui_instance.show_error.assert_called_with("Geçersiz Girdi", ANY)


    def test_start_clicking_no_trigger_key(self):
        self.app_core.trigger_key = None
        self.app_core.start_clicking()
        self.assertFalse(self.app_core.is_running)
        self.mock_ui_instance.show_warning.assert_called_once_with("Hata", ANY)

    def test_start_clicking_invalid_params(self):
        self.app_core.trigger_key = mock_pynput.keyboard.Key.f1 # Use global mock
        with patch.object(self.app_core, '_get_validated_params', return_value=None):
            self.app_core.start_clicking()
            self.assertFalse(self.app_core.is_running)
            # _get_validated_params itself shows error, so no new error here

    @patch('core.threading.Thread')
    def test_start_clicking_success(self, mock_thread_class):
        self.app_core.trigger_key = mock_pynput.keyboard.Key.f1 # Use global mock
        mock_thread_instance = MagicMock()
        mock_thread_class.return_value = mock_thread_instance

        self.app_core.start_clicking()

        self.assertTrue(self.app_core.is_running)
        self.assertEqual(self.app_core.click_count, 0)
        self.mock_ui_instance.update_click_count.assert_called_with(0)
        self.mock_ui_instance.update_status_display.assert_called_with(STATUS_RUNNING, ANY, True)
        self.mock_click_mode_instance.reset.assert_called() # Called again on start
        mock_thread_class.assert_called_once_with(target=self.app_core._click_loop, args=(ANY,), daemon=True)
        mock_thread_instance.start.assert_called_once()

    def test_stop_clicking(self):
        self.app_core.is_running = True # Simulate running state
        self.app_core.stop_clicking()
        self.assertFalse(self.app_core.is_running)
        self.mock_ui_instance.update_status_display.assert_called_with(ANY, ANY, False)

    def test_toggle_clicking(self):
        # Test starting
        with patch.object(self.app_core, 'start_clicking') as mock_start:
            self.app_core.is_running = False
            self.app_core.toggle_clicking()
            mock_start.assert_called_once()

        # Test stopping
        with patch.object(self.app_core, 'stop_clicking') as mock_stop:
            self.app_core.is_running = True
            self.app_core.toggle_clicking()
            mock_stop.assert_called_once()

    def test_set_assign_mode(self):
        self.app_core.set_assign_mode()
        self.assertTrue(self.app_core.is_assigning_key)
        self.mock_ui_instance.update_trigger_key_display.assert_called_once_with(ASSIGN_KEY_PROMPT, False)

    def test_assign_key_set(self):
        self.app_core.is_assigning_key = True
        # Use the mocked KeyCode from the global pynput mock
        new_key_instance = MagicMock(name="mocked_char_a_instance")
        new_key_instance.char = 'a' # Simulate a KeyCode with a char attribute
        mock_pynput.keyboard.KeyCode.return_value = new_key_instance
        # Actual key object passed to _assign_key can be this instance directly for test clarity
        # Or, if _assign_key is expected to receive the result of a KeyCode call:
        actual_key_obj_for_assignment = mock_pynput.keyboard.KeyCode(char='a')


        self.app_core._assign_key(actual_key_obj_for_assignment)

        self.assertFalse(self.app_core.is_assigning_key)
        self.assertEqual(self.app_core.trigger_key, actual_key_obj_for_assignment)
        self.mock_ui_instance.update_trigger_key_display.assert_called_with('A', True)

    def test_assign_key_cancel(self):
        self.app_core.is_assigning_key = True
        self.app_core.trigger_key = mock_pynput.keyboard.Key.f5 # Existing key

        self.app_core._assign_key(mock_pynput.keyboard.Key.esc)

        self.assertFalse(self.app_core.is_assigning_key)
        self.assertEqual(self.app_core.trigger_key, mock_pynput.keyboard.Key.f5) # Unchanged
        self.mock_ui_instance.update_trigger_key_display.assert_called_with('F5', True)

    def test_assign_key_cancel_no_prior_key(self):
        self.app_core.is_assigning_key = True
        self.app_core.trigger_key = None

        self.app_core._assign_key(mock_pynput.keyboard.Key.esc)

        self.assertFalse(self.app_core.is_assigning_key)
        self.assertIsNone(self.app_core.trigger_key)
        self.mock_ui_instance.update_trigger_key_display.assert_called_with(KEY_NOT_ASSIGNED, False)


    @patch('core.sys.exit')
    def test_emergency_shutdown(self, mock_sys_exit):
        self.app_core.is_running = True
        self.app_core.emergency_shutdown()
        self.assertFalse(self.app_core.is_running)
        self.mock_ui_instance.destroy.assert_called_once()
        mock_sys_exit.assert_called_once()

    def test_on_key_press_f12(self):
        with patch.object(self.app_core, 'emergency_shutdown') as mock_shutdown:
            self.app_core._on_key_press(mock_pynput.keyboard.Key.f12) # Use global mock
            self.mock_ui_instance.after.assert_called_with(0, mock_shutdown)

    def test_on_key_press_trigger(self):
        trigger_key_instance = MagicMock(name="trigger_t_instance") # Simulate a key instance
        mock_pynput.keyboard.KeyCode.return_value = trigger_key_instance
        trigger = mock_pynput.keyboard.KeyCode(char='t')

        self.app_core.trigger_key = trigger
        self.app_core.is_assigning_key = False

        with patch.object(self.app_core, 'toggle_clicking') as mock_toggle:
            self.app_core._on_key_press(trigger)
            # _on_key_press calls _process_key_event via ui.after
            # We need to call _process_key_event directly for this test unit
            self.app_core._process_key_event(trigger)
            mock_toggle.assert_called_once()

    def test_on_key_press_assigning(self):
        assign_key_instance = MagicMock(name="assign_k_instance")
        mock_pynput.keyboard.KeyCode.return_value = assign_key_instance
        assign_key = mock_pynput.keyboard.KeyCode(char='k')

        self.app_core.is_assigning_key = True

        with patch.object(self.app_core, '_assign_key') as mock_assign:
            self.app_core._on_key_press(assign_key)
            self.app_core._process_key_event(assign_key) # Simulate ui.after call
            mock_assign.assert_called_once_with(assign_key)

    # --- Test _click_loop ---
    # These are more complex integration-style tests for the loop

    @patch('core.time.perf_counter') # For precise sleep control
    @patch('core.random.uniform')
    def test_click_loop_single_click_left(self, mock_random_uniform, mock_perf_counter):
        global mock_pyautogui_module
        # Setup: one iteration of the loop
        self.app_core.is_running = True # Loop runs if true
        expected_mode_output = (10.0, 2, 3, 1.0) # cps, jitX, jitY, mult
        # Stop after one iteration for test AND return values
        def stop_loop_after_one_run_and_return(*args, **kwargs):
            self.app_core.is_running = False
            return expected_mode_output
        self.mock_click_mode_instance.get_next_action.side_effect = stop_loop_after_one_run_and_return

        # self.mock_click_mode_instance.get_next_action.return_value = (10.0, 2, 3, 1.0) # No longer needed, side_effect handles it
        mock_pyautogui_module.position.return_value = Point(100, 200) # x, y
        mock_random_uniform.return_value = 0.005 # 5ms random delay component

        # Mock perf_counter to control sleep timing
        # First call is start of sleep, second is end of sleep
        mock_perf_counter.side_effect = [time.perf_counter(), time.perf_counter() + 0.105]

        valid_params = self.app_core._get_validated_params() # Uses "Sol Tık"
        self.app_core._click_loop(valid_params)

        self.mock_click_mode_instance.get_next_action.assert_called_once()
        mock_pyautogui_module.position.assert_called_once()
        mock_pyautogui_module.click.assert_called_once_with(x=102, y=203, button='left')
        self.mock_ui_instance.after.assert_any_call(0, self.mock_ui_instance.update_realtime_cps, 10.0)
        self.mock_ui_instance.after.assert_any_call(0, self.mock_ui_instance.update_click_count, 1)
        self.assertEqual(self.app_core.click_count, 1)

        # Check delay calculation: base_delay = 1/10 = 0.1. rand_delay = 0.005. actual_delay = 0.105
        # perf_counter should have been called to sleep for ~0.105s
        self.assertGreaterEqual(mock_perf_counter.call_count, 2)


    @patch('core.time.perf_counter')
    @patch('core.random.uniform')
    def test_click_loop_both_buttons(self, mock_random_uniform, mock_perf_counter):
        global mock_pyautogui_module
        self.app_core.is_running = True
        expected_mode_output_both = (5.0, 1, 1, 1.0)
        def stop_loop_and_return_both(*args, **kwargs):
            self.app_core.is_running = False
            return expected_mode_output_both
        self.mock_click_mode_instance.get_next_action.side_effect = stop_loop_and_return_both
        # self.mock_click_mode_instance.get_next_action.return_value = (5.0, 1, 1, 1.0) # Covered by side_effect
        mock_pyautogui_module.position.return_value = Point(50, 50)
        mock_random_uniform.return_value = 0.0 # No random component for simplicity
        mock_perf_counter.side_effect = [time.perf_counter(), time.perf_counter() + 0.2] # 1/5 = 0.2s delay

        # Modify settings for "Sol ve Sağ Tık"
        settings = self.mock_ui_instance.get_current_settings()
        settings['mouse_button_pref'] = "Sol ve Sağ Tık"
        self.mock_ui_instance.get_current_settings.return_value = settings

        valid_params = self.app_core._get_validated_params()
        self.app_core._click_loop(valid_params)

        mock_pyautogui_module.click.assert_any_call(x=51, y=51, button='left')
        mock_pyautogui_module.click.assert_any_call(x=51, y=51, button='right')
        self.assertEqual(mock_pyautogui_module.click.call_count, 2)
        self.assertEqual(self.app_core.click_count, 2) # Both clicks counted
        self.mock_ui_instance.after.assert_any_call(0, self.mock_ui_instance.update_click_count, 2)

    @patch('core.time.perf_counter')
    def test_click_loop_mode_signals_stop(self, mock_perf_counter):
        global mock_pyautogui_module
        self.app_core.is_running = True
        # Mode returns 0 CPS to signal stop
        self.mock_click_mode_instance.get_next_action.return_value = (0, 0, 0, 1.0)

        valid_params = self.app_core._get_validated_params()

        # Mock ui.after to immediately execute the passed function
        def immediate_after_call(delay, func, *args):
            func(*args)
        self.mock_ui_instance.after.side_effect = immediate_after_call

        self.app_core._click_loop(valid_params)

        self.mock_click_mode_instance.get_next_action.assert_called_once()
        # stop_clicking should be called via ui.after
        self.assertFalse(self.app_core.is_running) # State should be updated by stop_clicking
        self.mock_ui_instance.update_status_display.assert_called_with(ANY, ANY, False)


    @patch('core.time.perf_counter')
    def test_click_loop_stop_requested_after_cycle(self, mock_perf_counter):
        global mock_pyautogui_module
        self.app_core.is_running = True
        self.app_core._stop_requested_after_cycle = True # Pre-set the flag

        # Mode returns valid CPS, but flag should stop it
        self.mock_click_mode_instance.get_next_action.return_value = (10.0, 1, 1, 1.0)

        valid_params = self.app_core._get_validated_params()

        def immediate_after_call(delay, func, *args): func(*args)
        self.mock_ui_instance.after.side_effect = immediate_after_call # To make stop_clicking run immediately

        self.app_core._click_loop(valid_params)

        # Loop should exit before trying to click or process mode output
        self.mock_click_mode_instance.get_next_action.assert_not_called()
        mock_pyautogui_module.click.assert_not_called() # Use the global mock
        self.assertFalse(self.app_core.is_running) # State updated by stop_clicking


    def test_stop_clicking_after_current_cycle_method(self):
        self.assertFalse(self.app_core._stop_requested_after_cycle)
        self.app_core.stop_clicking_after_current_cycle()
        self.assertTrue(self.app_core._stop_requested_after_cycle)


if __name__ == '__main__':
    unittest.main()
