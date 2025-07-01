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


    def test_ui_initialization(self):
        self.assertEqual(self.app_ui.title(), "Gerçekçi Jitter Simülatörü v5.0")
        self.assertIsNotNone(self.app_ui.status_label)
        self.assertIsNotNone(self.app_ui.toggle_button)
        self.mock_app_core.on_mode_changed.assert_called_once_with("Sabit") # Initial mode

    def test_update_status_display_running(self):
        self.app_ui.update_status_display(STATUS_RUNNING, "green", is_running=True)
        self.assertEqual(self.app_ui.status_label.cget("text"), STATUS_RUNNING)
        self.assertEqual(self.app_ui.status_label.cget("foreground"), "green")
        self.assertEqual(self.app_ui.toggle_button.cget("text"), "Durdur")

        # Check if settings widgets are disabled
        # Example: cps_scale (assuming it's in settings_widgets implicitly or explicitly)
        # Need to ensure settings_widgets is populated correctly for this test
        # For instance, mode_combo is added to settings_widgets
        self.assertEqual(self.app_ui.mode_combo.cget("state"), "disabled")
        self.assertEqual(self.app_ui.cps_scale.cget("state"), "disabled")


    def test_update_status_display_idle(self):
        self.app_ui.update_status_display(STATUS_IDLE, "black", is_running=False)
        self.assertEqual(self.app_ui.status_label.cget("text"), STATUS_IDLE)
        self.assertEqual(self.app_ui.toggle_button.cget("text"), "Başlat")
        self.assertEqual(self.app_ui.mode_combo.cget("state"), "readonly") # Combobox specific
        self.assertEqual(self.app_ui.cps_scale.cget("state"), "normal")


    def test_update_realtime_cps(self):
        self.app_ui.update_realtime_cps(12.34)
        self.assertEqual(self.app_ui.real_time_cps_label.cget("text"), "Anlık CPS: 12.3")

    def test_update_click_count(self):
        self.app_ui.update_click_count(123)
        self.assertEqual(self.app_ui.click_count_label.cget("text"), "Toplam Tıklama: 123")

    def test_update_trigger_key_display(self):
        self.app_ui.update_trigger_key_display("F1", is_assigned=True)
        self.assertEqual(self.app_ui.trigger_key_label.cget("text"), "F1")
        self.assertIn("green", str(self.app_ui.trigger_key_label.cget("foreground"))) # Color check

        self.app_ui.update_trigger_key_display(KEY_NOT_ASSIGNED, is_assigned=False)
        self.assertEqual(self.app_ui.trigger_key_label.cget("text"), KEY_NOT_ASSIGNED)
        self.assertIn("red", str(self.app_ui.trigger_key_label.cget("foreground")))

        self.app_ui.update_trigger_key_display(ASSIGN_KEY_PROMPT, is_assigned=False) # is_assigned might be true too
        self.assertEqual(self.app_ui.trigger_key_label.cget("text"), ASSIGN_KEY_PROMPT)
        self.assertIn("blue", str(self.app_ui.trigger_key_label.cget("foreground")))


    @patch('ui.messagebox')
    def test_show_error_warning(self, mock_messagebox):
        self.app_ui.show_error("Error Title", "Error Message")
        mock_messagebox.showerror.assert_called_once_with("Error Title", "Error Message")

        self.app_ui.show_warning("Warning Title", "Warning Message")
        mock_messagebox.showwarning.assert_called_once_with("Warning Title", "Warning Message")

    def test_get_current_settings(self):
        # Set some UI values
        self.app_ui.cps_var.set(22.5)
        self.app_ui.timing_rand_var.set("25")
        self.app_ui.jitter_intensity_var.set("7")
        self.app_ui.mouse_button_var.set("Sağ Tık")
        self.app_ui.cps_mode_var.set("Patlama")
        self.app_ui.burst_duration_var.set("3.5")
        self.app_ui.min_cps_random_var.set("3.0")
        self.app_ui.max_cps_random_var.set("8.0")
        self.app_ui.click_pattern_var.set("50-150")

        settings = self.app_ui.get_current_settings()

        self.assertEqual(settings['peak_cps'], 22.5)
        self.assertEqual(settings['timing_rand_ms'], "25")
        self.assertEqual(settings['jitter_px'], "7")
        self.assertEqual(settings['mouse_button_pref'], "Sağ Tık")
        self.assertEqual(settings['mode'], "Patlama")
        self.assertEqual(settings['burst_duration'], "3.5")

        # Test other modes' settings retrieval by changing mode
        self.app_ui.cps_mode_var.set("Rastgele Aralık")
        settings_random = self.app_ui.get_current_settings()
        self.assertEqual(settings_random['min_cps_random'], "3.0")
        self.assertEqual(settings_random['max_cps_random'], "8.0")

        self.app_ui.cps_mode_var.set("Pattern (Desen)")
        settings_pattern = self.app_ui.get_current_settings()
        self.assertEqual(settings_pattern['click_pattern'], "50-150")


    def test_on_mode_change_ui_visibility(self):
        # Test Patlama mode
        self.app_ui.mode_combo.set("Patlama") # This should trigger _on_mode_change
        self.app_ui._on_mode_change() # Call directly to ensure it runs
        self.assertTrue(self.app_ui.burst_frame.winfo_ismapped())
        self.assertFalse(self.app_ui.random_interval_frame.winfo_ismapped())
        self.assertFalse(self.app_ui.pattern_mode_frame.winfo_ismapped())
        self.mock_app_core.on_mode_changed.assert_called_with("Patlama")
        self.assertTrue(self.app_ui.cps_scale.winfo_ismapped())


        # Test Rastgele Aralık mode
        self.app_ui.mode_combo.set("Rastgele Aralık")
        self.app_ui._on_mode_change()
        self.assertFalse(self.app_ui.burst_frame.winfo_ismapped())
        self.assertTrue(self.app_ui.random_interval_frame.winfo_ismapped())
        self.assertFalse(self.app_ui.pattern_mode_frame.winfo_ismapped())
        self.mock_app_core.on_mode_changed.assert_called_with("Rastgele Aralık")
        self.assertTrue(self.app_ui.cps_scale.winfo_ismapped())

        # Test Pattern (Desen) mode
        self.app_ui.mode_combo.set("Pattern (Desen)")
        self.app_ui._on_mode_change()
        self.assertFalse(self.app_ui.burst_frame.winfo_ismapped())
        self.assertFalse(self.app_ui.random_interval_frame.winfo_ismapped())
        self.assertTrue(self.app_ui.pattern_mode_frame.winfo_ismapped())
        self.mock_app_core.on_mode_changed.assert_called_with("Pattern (Desen)")
        # Main CPS scale should be hidden for Pattern mode
        self.assertFalse(self.app_ui.cps_scale.winfo_ismapped())
        self.assertFalse(self.app_ui.cps_title_label.winfo_ismapped())
        self.assertFalse(self.app_ui.cps_label_display.winfo_ismapped())

        # Test Sabit mode (default)
        self.app_ui.mode_combo.set("Sabit")
        self.app_ui._on_mode_change()
        self.assertFalse(self.app_ui.burst_frame.winfo_ismapped())
        self.assertFalse(self.app_ui.random_interval_frame.winfo_ismapped())
        self.assertFalse(self.app_ui.pattern_mode_frame.winfo_ismapped())
        self.mock_app_core.on_mode_changed.assert_called_with("Sabit")
        self.assertTrue(self.app_ui.cps_scale.winfo_ismapped())


if __name__ == '__main__':
    # This setup allows running tests directly, but `python -m unittest discover` is preferred
    # Ensure that if run directly, the Tkinter issues in setUp are handled.
    # For CI, it's crucial that either Tkinter is fully mocked or a virtual display is used.
    unittest.main()
