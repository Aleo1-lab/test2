import pyautogui
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

import threading
import time
import random
import sys
from pynput import keyboard

from ui import (AutoClickerUI, STATUS_RUNNING, STATUS_IDLE, STATUS_STOPPED,
                STATUS_ERROR, ASSIGN_KEY_PROMPT, KEY_NOT_ASSIGNED,
                COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_BLACK) # Added COLOR_BLACK
from click_modes import get_click_mode

class AppCore:
    def __init__(self):
        self.ui = AutoClickerUI(self)
        self.is_running = False
        self.click_thread = None
        self.trigger_key = None
        self.is_assigning_key = False
        self.click_count = 0
        self.current_click_mode = None
        self._stop_requested_after_cycle = False # For modes like 'Patlama'

        self._start_keyboard_listener()
        self.on_mode_changed(self.ui.cps_mode_var.get()) # Initialize click mode

    def on_mode_changed(self, mode_name: str):
        new_mode_instance = None
        try:
            new_mode_instance = get_click_mode(mode_name, self)
        except ValueError as e:
            self.ui.show_error("Mod Hatası", str(e))
            if self.ui.mode_combo: # Check if UI is fully initialized
                 self.ui.mode_combo.set("Sabit") # Fallback to "Sabit"
                 try:
                     new_mode_instance = get_click_mode("Sabit", self) # Attempt to get fallback
                 except ValueError: # Should not happen if "Sabit" is always valid
                     print("APPCORE_CRITICAL: Fallback mode 'Sabit' also failed to load.")
                     # self.current_click_mode will remain whatever it was, or None

        self.current_click_mode = new_mode_instance
        if self.current_click_mode:
            self.current_click_mode.reset()
        else:
            # This case means even fallback failed or was not attempted.
            print(f"APPCORE_WARNING: No click mode (not even fallback) could be set for mode_name '{mode_name}'.")
            # Consider what state self.current_click_mode should be in if everything fails.
            # Maybe set it to a NoOpClickMode or ensure parts of the app are disabled.

    def _get_validated_params(self) -> dict | None:
        """Validates UI settings and returns them or None if invalid."""
        raw_settings = self.ui.get_current_settings()
        try:
            params = {
                'peak_cps': float(raw_settings['peak_cps']),
                'timing_rand_ms': int(raw_settings['timing_rand_ms']),
                'jitter_px': int(raw_settings['jitter_px']),
                'mouse_button_pref': raw_settings['mouse_button_pref'],
                'mode': raw_settings['mode']
            }
            if params['peak_cps'] <=0: raise ValueError("CPS pozitif olmalı.")
            if params['timing_rand_ms'] < 0: raise ValueError("Zamanlama rastgeleliği negatif olamaz.")
            if params['jitter_px'] < 0: raise ValueError("Jitter yoğunluğu negatif olamaz.")

            if params['mode'] == 'Patlama':
                params['burst_duration'] = float(raw_settings['burst_duration'])
                if params['burst_duration'] <= 0: raise ValueError("Patlama süresi pozitif olmalı.")
            elif params['mode'] == 'Rastgele Aralık':
                params['min_cps_random'] = float(raw_settings['min_cps_random'])
                params['max_cps_random'] = float(raw_settings['max_cps_random'])
                if params['min_cps_random'] <= 0 or params['max_cps_random'] <= 0:
                    raise ValueError("Rastgele Aralık CPS değerleri pozitif olmalı.")
                if params['min_cps_random'] > params['max_cps_random']:
                    raise ValueError("Min CPS, Max CPS'den büyük olamaz.")
            elif params['mode'] == 'Pattern (Desen)':
                params['click_pattern'] = raw_settings['click_pattern']
                if not params['click_pattern'].strip():
                    raise ValueError("Pattern boş olamaz.")

            # Add validation for other modes if they have specific params
            return params
        except (ValueError, TypeError) as e:
            self.ui.update_status_display(STATUS_ERROR, COLOR_RED, self.is_running)
            self.ui.show_error("Geçersiz Girdi", f"Lütfen ayarları kontrol edin.\nHata: {e}")
            return None

    def _set_program_state(self, running: bool):
        self.is_running = running
        if running:
            status_text, color = STATUS_RUNNING, COLOR_GREEN
        else:
            status_text, color = STATUS_STOPPED if self.click_thread else STATUS_IDLE, COLOR_BLACK

        self.ui.update_status_display(status_text, color, self.is_running)

    def start_clicking(self):
        if self.is_running: return
        if not self.trigger_key:
            self.ui.show_warning("Hata", "Lütfen önce bir tetikleyici tuş atayın!")
            return

        params = self._get_validated_params()
        if not params: return

        if not self.current_click_mode:
            self.ui.show_error("Hata", "Tıklama modu seçilemedi.")
            return
        self.current_click_mode.reset() # Reset mode state at the start of a new session

        self.click_count = 0
        self.ui.update_click_count(self.click_count)
        self._set_program_state(True)
        self._stop_requested_after_cycle = False

        self.click_thread = threading.Thread(target=self._click_loop, args=(params,), daemon=True)
        self.click_thread.start()

    def _click_loop(self, params: dict):
        start_time = time.time()

        while self.is_running:
            if self._stop_requested_after_cycle:
                self.ui.after(0, self.stop_clicking)
                break
            try:
                elapsed_time = time.time() - start_time

                current_cps, jitter_x, jitter_y, _ = self.current_click_mode.get_next_action(params, elapsed_time)

                if current_cps <= 0: # Mode might signal to stop (e.g. Patlama finished)
                    if self.is_running: # Ensure stop_clicking is called only if it was running
                         self.ui.after(0, self.stop_clicking)
                    break

                current_cps = max(0.1, current_cps) # Prevent division by zero for delay calculation
                self.ui.after(0, self.ui.update_realtime_cps, current_cps) # Update UI with effective CPS

                # Determine mouse button(s) to click based on UI preference
                mouse_button_pref = params['mouse_button_pref']
                buttons_to_click = []
                if mouse_button_pref == "Sol Tık":
                    buttons_to_click.append('left')
                elif mouse_button_pref == "Sağ Tık":
                    buttons_to_click.append('right')
                elif mouse_button_pref == "Sol ve Sağ Tık": # TODO: Add user choice for simultaneous or alternating
                    buttons_to_click.extend(['left', 'right']) # For now, click both nearly simultaneously

                pos = pyautogui.position()
                for btn in buttons_to_click:
                    pyautogui.click(x=pos.x + int(jitter_x), y=pos.y + int(jitter_y), button=btn)
                    # If clicking both, add a tiny delay between them if desired, or handle alternating logic
                    if len(buttons_to_click) > 1: time.sleep(0.001) # Minimal delay

                self.click_count += len(buttons_to_click) # Count each click if multiple buttons are pressed
                self.ui.after(0, self.ui.update_click_count, self.click_count)

                # --- Delay Calculation ---
                # Base delay determined by the current CPS from the click mode
                base_delay = 1.0 / current_cps
                # Add timing randomness based on UI settings
                rand_delay_ms = params['timing_rand_ms']
                rand_delay_s = random.uniform(-rand_delay_ms / 1000.0, rand_delay_ms / 1000.0)
                # Ensure delay is not excessively small or negative
                actual_delay = max(0.001, base_delay + rand_delay_s)

                # --- Precise Sleep ---
                # Use perf_counter for a more precise sleep than time.sleep() for short durations
                target_time = time.perf_counter() + actual_delay
                while time.perf_counter() < target_time:
                    if not self.is_running: break # Allow immediate exit if clicking is stopped

                # --- Update time_counter for Perlin-like modes ---
                if hasattr(self.current_click_mode, 'time_counter') and isinstance(self.current_click_mode.time_counter, float):
                    # Provide actual_delay to modes that use it for their internal time_counter progression.
                    # The multiplier (e.g., 0.5) controls how fast the Perlin noise evolves relative to click speed.
                     if current_cps > 0 : self.current_click_mode.time_counter += actual_delay * 0.5

            except Exception as e:
                print(f"Click Loop Hatası: {e}") # Log to console for debugging
                self.ui.after(0, self.stop_clicking) # Ensure UI updates on main thread
                break

        # Ensure state is updated if loop exits unexpectedly
        if self.is_running:
            self.ui.after(0, self._set_program_state, False)


    def stop_clicking(self):
        if not self.is_running: return
        self._set_program_state(False)
        # self.click_thread = None # Thread will exit on its own due to self.is_running

    def stop_clicking_after_current_cycle(self):
        """Used by click modes (like Patlama) to signal graceful stop."""
        self._stop_requested_after_cycle = True

    def toggle_clicking(self):
        if self.is_running:
            self.stop_clicking()
        else:
            self.start_clicking()

    def set_assign_mode(self):
        self.is_assigning_key = True
        self.ui.update_trigger_key_display(ASSIGN_KEY_PROMPT, False)

    def _assign_key(self, key):
        def format_key_name(k): # Helper to format key names consistently
            if hasattr(k, 'char') and k.char: return k.char.upper()
            if hasattr(k, 'name'): return k.name.upper()
            return str(k).split('.')[-1].upper()

        if not self.is_assigning_key: return
        self.is_assigning_key = False

        if key == keyboard.Key.esc:
            if self.trigger_key:
                self.ui.update_trigger_key_display(format_key_name(self.trigger_key), True)
            else:
                self.ui.update_trigger_key_display(KEY_NOT_ASSIGNED, False)
            return

        self.trigger_key = key
        self.ui.update_trigger_key_display(format_key_name(key), True)

    def _start_keyboard_listener(self):
        listener = keyboard.Listener(on_press=self._on_key_press)
        listener.daemon = True # Ensures thread exits when main program exits
        listener.start()

    def _on_key_press(self, key):
        if key == keyboard.Key.f12:
            self.ui.after(0, self.emergency_shutdown) # Ensure UI operations on main thread
            return

        # Process other keys in the main thread via `after` to avoid Tkinter issues from threads
        self.ui.after(0, self._process_key_event, key)

    def _process_key_event(self, key):
        if self.is_assigning_key:
            self._assign_key(key)
        elif self.trigger_key and key == self.trigger_key:
            self.toggle_clicking()

    def emergency_shutdown(self):
        print("Acil Durum Kapatma... Program sonlandırılıyor...")
        self.is_running = False # Stop any active click loops
        if self.ui:
            self.ui.destroy()
        sys.exit()

    def run(self):
        self.ui.mainloop()

if __name__ == "__main__":
    # This check prevents running when imported, similar to the original app.
    # To run the application, you would now execute this core.py file.
    core_app = AppCore()
    core_app.run()
