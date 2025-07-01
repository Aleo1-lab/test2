import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk

# Add project root to sys.path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui import AutoClickerUI, STATUS_IDLE, STATUS_RUNNING, KEY_NOT_ASSIGNED, ASSIGN_KEY_PROMPT

# Mock pynput keyboard if ui directly imports or uses it (it doesn't directly, core does)

class TestAutoClickerUI(unittest.TestCase):

    @patch('ui.ttk.Style') # Patch ttk.Style to avoid "TclError:can't find package BWidget"
    def setUp(self, mock_style):
        self.mock_app_core = MagicMock()
        # Prevent actual Tk window from opening during tests
        # We can't easily patch tk.Tk itself without major issues,
        # so we'll rely on not calling mainloop and checking widget states.
        # For more complex UI tests, a library like pytest-qt or specific tkinter testing tools might be used.

        # To prevent actual window creation, we can try to patch `super().__init__()`
        # or more granularly, methods that would cause issues.
        # For now, we assume that not calling mainloop is sufficient for basic tests.
        # If Tk complains about no default root, we might need to create a dummy root.
        try:
            self.root = tk.Tk()
            self.root.withdraw() # Hide the window
        except tk.TclError: # Happens in environments without a display (like CI)
             print("Tkinter TclError: No display available. UI tests will be limited.")
             self.root = None # Or a mock Tk object
             # If self.root is None, many tests might fail.
             # A better approach for CI is to use a virtual display like Xvfb.
             # For this exercise, we'll proceed and see what breaks.
             # If it's too problematic, we'll have to mock Tkinter more heavily.

        if self.root:
            self.app_ui = AutoClickerUI(self.mock_app_core)
        else: # If root creation failed, create UI with a mocked Tk part
            with patch('tkinter.Tk') as MockTk:
                 # This is tricky because AutoClickerUI inherits from tk.Tk
                 # A simple patch might not be enough.
                 # Let's assume for now self.root works or tests will show limitations.
                 # If Tk cannot be initialized, we cannot test the UI class directly.
                 # We might need to test its methods in isolation if they don't depend on Tk state.
                 pass # This path means UI tests will likely fail or need to be skipped.

        # If self.root is None, self.app_ui won't be properly initialized.
        # Add a check here.
        if not hasattr(self, 'app_ui') or not self.app_ui:
            print("Skipping UI tests as Tkinter could not be initialized.")
            self.skipTest("Tkinter initialization failed. Cannot run UI tests.")


    def tearDown(self):
        if hasattr(self, 'app_ui') and self.app_ui:
            try:
                self.app_ui.destroy()
            except tk.TclError: # Can happen if already destroyed or during CI issues
                pass
        if self.root:
            try:
                self.root.destroy()
            except tk.TclError:
                pass


from ui import AutoClickerUI, STATUS_IDLE, STATUS_RUNNING, STATUS_STOPPED, KEY_NOT_ASSIGNED, ASSIGN_KEY_PROMPT, COLOR_GREEN, COLOR_RED, COLOR_BLUE

# Mock pynput keyboard if ui directly imports or uses it (it doesn't directly, core does)

class TestAutoClickerUI(unittest.TestCase):

    @patch('ui.ttk.Style') # Patch ttk.Style to avoid "TclError:can't find package BWidget"
    def setUp(self, mock_style):
        self.mock_app_core = MagicMock()
        # Mock methods on app_core that UI calls during init or tests
        self.mock_app_core.on_mode_changed = MagicMock()
        self.mock_app_core.set_assign_mode = MagicMock()
        self.mock_app_core.emergency_shutdown = MagicMock()

        # Simulate that mode loading in AppCore is successful
        # This is to prevent _on_mode_change from potentially trying to reset UI to "Sabit"
        # if AppCore reported a failure (which it might if not fully mocked for this UI test).
        # For left tab during UI init
        self.mock_app_core.left_click_mode = MagicMock() # Represents a successfully loaded mode
        # For right tab during UI init
        self.mock_app_core.right_click_mode = MagicMock()


        # Prevent actual Tk window from opening during tests
        try:
            self.root = tk.Tk()
            self.root.withdraw() # Hide the window
        except tk.TclError:
             print("Tkinter TclError: No display available. UI tests will be limited.")
             self.root = None

        if self.root:
            # tk.Tk() # Ensure a root window exists for widget creation if not using self.root
            self.app_ui = AutoClickerUI(self.mock_app_core)
        else:
            self.skipTest("Tkinter initialization failed. Cannot run UI tests.")


    def tearDown(self):
        if hasattr(self, 'app_ui') and self.app_ui:
            try:
                self.app_ui.destroy()
            except tk.TclError:
                pass
        if self.root: # Destroy the explicit root if created
            try:
                self.root.destroy()
            except tk.TclError:
                pass


    def test_ui_initialization(self):
        self.assertEqual(self.app_ui.title(), "Gelişmiş Otomatik Tıklayıcı v6.0") # Updated title
        self.assertIsNotNone(self.app_ui.status_label)
        self.assertIsNotNone(self.app_ui.real_time_cps_label)
        self.assertIsNotNone(self.app_ui.left_trigger_key_label)
        self.assertIsNotNone(self.app_ui.right_trigger_key_label)
        # Check that on_mode_changed was called for both tabs during UI init
        self.mock_app_core.on_mode_changed.assert_any_call("Sabit", 'left')
        self.mock_app_core.on_mode_changed.assert_any_call("Sabit", 'right')
        self.assertEqual(self.mock_app_core.on_mode_changed.call_count, 2)


    def test_update_status_display_various_states(self):
        # Test Idle state
        self.app_ui.update_status_display(STATUS_IDLE, "black", is_running=False)
        self.assertEqual(self.app_ui.status_label.cget("text"), STATUS_IDLE)

        # Check if settings widgets are enabled (example: left tab's mode_combo and cps_scale)
        left_widgets = self.app_ui.left_click_widgets
        self.assertEqual(left_widgets['mode_combo'].cget("state"), "readonly")
        self.assertEqual(left_widgets['cps_scale'].cget("state"), "normal")

        # Test Running state (e.g., "SOL TIK AKTİF")
        left_active_status = "Durum: SOL TIK AKTİF"
        self.app_ui.update_status_display(left_active_status, COLOR_GREEN, is_running=True)
        self.assertEqual(self.app_ui.status_label.cget("text"), left_active_status)
        self.assertEqual(str(self.app_ui.status_label.cget("foreground")), COLOR_GREEN)

        # Check if settings widgets are disabled
        self.assertEqual(left_widgets['mode_combo'].cget("state"), "disabled")
        self.assertEqual(left_widgets['cps_scale'].cget("state"), "disabled")
        # Also check a global settings widget like assign button
        # Assuming assign_left_button is one of the first in self.app_ui.settings_widgets
        assign_button_example = next((w for w in self.app_ui.settings_widgets if isinstance(w, ttk.Button) and "Sol Tık Tetikleyici Ata" in w.cget("text")), None)
        if assign_button_example:
             self.assertEqual(assign_button_example.cget("state"), "disabled")


    def test_update_realtime_cps(self):
        self.app_ui.update_realtime_cps(12.34, "Sol")
        self.assertEqual(self.app_ui.real_time_cps_label.cget("text"), "Anlık Sol CPS: 12.3")
        self.app_ui.update_realtime_cps(8.76, "Sağ")
        self.assertEqual(self.app_ui.real_time_cps_label.cget("text"), "Anlık Sağ CPS: 8.8")
        self.app_ui.update_realtime_cps(10.0) # No type
        self.assertEqual(self.app_ui.real_time_cps_label.cget("text"), "Anlık CPS: 10.0")


    def test_update_click_count(self):
        self.app_ui.update_click_count(123)
        self.assertEqual(self.app_ui.click_count_label.cget("text"), "Toplam Tıklama: 123")


    def test_update_trigger_key_display_left_right(self):
        # Test Left Trigger
        self.app_ui.update_trigger_key_display("F1", is_assigned=True, trigger_type='left')
        self.assertEqual(self.app_ui.left_trigger_key_label.cget("text"), "F1")
        self.assertIn(COLOR_GREEN, str(self.app_ui.left_trigger_key_label.cget("foreground")))

        self.app_ui.update_trigger_key_display(KEY_NOT_ASSIGNED, is_assigned=False, trigger_type='left')
        self.assertEqual(self.app_ui.left_trigger_key_label.cget("text"), KEY_NOT_ASSIGNED)
        self.assertIn(COLOR_RED, str(self.app_ui.left_trigger_key_label.cget("foreground")))

        assign_prompt_left = f"{ASSIGN_KEY_PROMPT.split('...')[0]} (LEFT)... (İptal: ESC)"
        self.app_ui.update_trigger_key_display(ASSIGN_KEY_PROMPT, is_assigned=False, trigger_type='left')
        self.assertEqual(self.app_ui.left_trigger_key_label.cget("text"), assign_prompt_left)
        self.assertIn(COLOR_BLUE, str(self.app_ui.left_trigger_key_label.cget("foreground")))

        # Test Right Trigger
        self.app_ui.update_trigger_key_display("MOUSE_RIGHT", is_assigned=True, trigger_type='right')
        self.assertEqual(self.app_ui.right_trigger_key_label.cget("text"), "MOUSE_RIGHT")
        self.assertIn(COLOR_GREEN, str(self.app_ui.right_trigger_key_label.cget("foreground")))

        assign_prompt_right = f"{ASSIGN_KEY_PROMPT.split('...')[0]} (RIGHT)... (İptal: ESC)"
        self.app_ui.update_trigger_key_display(ASSIGN_KEY_PROMPT, is_assigned=False, trigger_type='right')
        self.assertEqual(self.app_ui.right_trigger_key_label.cget("text"), assign_prompt_right)
        self.assertIn(COLOR_BLUE, str(self.app_ui.right_trigger_key_label.cget("foreground")))


    @patch('ui.messagebox')
    def test_show_error_warning(self, mock_messagebox):
        self.app_ui.show_error("Error Title", "Error Message")
        mock_messagebox.showerror.assert_called_once_with("Error Title", "Error Message")

        self.app_ui.show_warning("Warning Title", "Warning Message")
        mock_messagebox.showwarning.assert_called_once_with("Warning Title", "Warning Message")


    def test_get_current_settings_both_tabs(self):
        # Set UI values for Left Tab
        left_widgets = self.app_ui.left_click_widgets
        left_widgets['cps_var'].set(20.0)
        left_widgets['timing_rand_var'].set("20")
        left_widgets['jitter_intensity_var'].set("2")
        left_widgets['cps_mode_var'].set("Patlama")
        left_widgets['burst_duration_var'].set("2.5")

        # Set UI values for Right Tab
        right_widgets = self.app_ui.right_click_widgets
        right_widgets['cps_var'].set(10.0)
        right_widgets['timing_rand_var'].set("30")
        right_widgets['jitter_intensity_var'].set("6")
        right_widgets['cps_mode_var'].set("Rastgele Aralık")
        right_widgets['min_cps_random_var'].set("4.0")
        right_widgets['max_cps_random_var'].set("12.0")


        all_settings = self.app_ui.get_current_settings()

        # Check Left Tab settings
        left_settings = all_settings['left']
        self.assertEqual(left_settings['peak_cps'], 20.0)
        self.assertEqual(left_settings['timing_rand_ms'], "20")
        self.assertEqual(left_settings['jitter_px'], "2")
        self.assertEqual(left_settings['mode'], "Patlama")
        self.assertEqual(left_settings['burst_duration'], "2.5")

        # Check Right Tab settings
        right_settings = all_settings['right']
        self.assertEqual(right_settings['peak_cps'], 10.0)
        self.assertEqual(right_settings['timing_rand_ms'], "30")
        self.assertEqual(right_settings['jitter_px'], "6")
        self.assertEqual(right_settings['mode'], "Rastgele Aralık")
        self.assertEqual(right_settings['min_cps_random'], "4.0")
        self.assertEqual(right_settings['max_cps_random'], "12.0")


    def test_on_mode_change_ui_visibility_per_tab(self):
        # --- Test Left Tab ---
        left_widgets = self.app_ui.left_click_widgets
        # Patlama mode on Left Tab
        left_widgets['mode_combo'].set("Patlama")
        self.app_ui._on_mode_change(event=None, click_type='left')
        self.assertTrue(left_widgets['burst_frame'].winfo_ismapped())
        self.assertFalse(left_widgets['random_interval_frame'].winfo_ismapped())
        self.assertFalse(left_widgets['pattern_mode_frame'].winfo_ismapped())
        self.mock_app_core.on_mode_changed.assert_called_with("Patlama", 'left')
        self.assertTrue(left_widgets['cps_scale'].winfo_ismapped())

        # Pattern mode on Left Tab (CPS scale should hide)
        left_widgets['mode_combo'].set("Pattern (Desen)")
        self.app_ui._on_mode_change(event=None, click_type='left')
        self.assertTrue(left_widgets['pattern_mode_frame'].winfo_ismapped())
        self.assertFalse(left_widgets['burst_frame'].winfo_ismapped())
        self.assertFalse(left_widgets['cps_scale'].winfo_ismapped())
        self.mock_app_core.on_mode_changed.assert_called_with("Pattern (Desen)", 'left')

        # --- Test Right Tab (independent of Left Tab's state) ---
        right_widgets = self.app_ui.right_click_widgets
        # Initially, left tab is Pattern, right tab should be default (Sabit) or its last set mode.
        # Let's set Right Tab to Rastgele Aralık
        right_widgets['mode_combo'].set("Rastgele Aralık")
        self.app_ui._on_mode_change(event=None, click_type='right')

        # Verify Right Tab
        self.assertTrue(right_widgets['random_interval_frame'].winfo_ismapped())
        self.assertFalse(right_widgets['burst_frame'].winfo_ismapped())
        self.assertFalse(right_widgets['pattern_mode_frame'].winfo_ismapped())
        self.mock_app_core.on_mode_changed.assert_called_with("Rastgele Aralık", 'right')
        self.assertTrue(right_widgets['cps_scale'].winfo_ismapped())

        # Verify Left Tab is still in Pattern mode and its UI reflects that
        self.assertTrue(left_widgets['pattern_mode_frame'].winfo_ismapped())
        self.assertFalse(left_widgets['cps_scale'].winfo_ismapped())


if __name__ == '__main__':
    unittest.main()
