import pyautogui
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

import threading
import time
import random
import sys
from pynput import keyboard, mouse # Added mouse

from ui import (AutoClickerUI, STATUS_RUNNING, STATUS_IDLE, STATUS_STOPPED,
                STATUS_ERROR, ASSIGN_KEY_PROMPT, KEY_NOT_ASSIGNED,
                COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_BLACK)
from click_modes import get_click_mode

class AppCore:
    def __init__(self):
        self.ui = AutoClickerUI(self)
        self.is_running = False
        self.click_thread = None
        self.trigger_input = None # Can be keyboard.Key, keyboard.KeyCode, or mouse.Button
        self.is_assigning_key = False
        self.click_count = 0
        self._stop_requested_after_cycle = False

        # Click modes and params for left and right
        self.left_click_mode = None
        self.right_click_mode = None
        self.active_click_params = {} # Will hold validated params for active configuration

        self._start_listeners() # Starts both keyboard and mouse listeners

        # Initialize click modes for both left and right tabs
        # The UI calls on_mode_changed during its __init__ for both tabs
        # So, we can expect left_click_mode and right_click_mode to be set up.
        # The UI's __init__ will call self.on_mode_changed for 'left' and 'right'
        # via its own _on_mode_change, so direct calls here are not needed and
        # could be premature if UI elements aren't fully ready.
        pass # Click modes are initialized by UI callbacks.


    def on_mode_changed(self, mode_name: str, click_type: str):
        """Handles changes in click mode for 'left' or 'right' click types."""
        new_mode_instance = None
        ui_widgets = self.ui.left_click_widgets if click_type == 'left' else self.ui.right_click_widgets
        try:
            new_mode_instance = get_click_mode(mode_name, self) # Pass self (AppCore)
        except ValueError as e:
            self.ui.show_error(f"{click_type.capitalize()} Mod Hatası", str(e))
            if ui_widgets.get('mode_combo'):
                 ui_widgets['mode_combo'].set("Sabit") # Fallback
                 try:
                     new_mode_instance = get_click_mode("Sabit", self)
                 except ValueError:
                     print(f"APPCORE_CRITICAL: Fallback mode 'Sabit' for {click_type} also failed.")

        if click_type == 'left':
            self.left_click_mode = new_mode_instance
            if self.left_click_mode: self.left_click_mode.reset()
        elif click_type == 'right':
            self.right_click_mode = new_mode_instance
            if self.right_click_mode: self.right_click_mode.reset()

        if not new_mode_instance:
            print(f"APPCORE_WARNING: No click mode set for {click_type} with mode_name '{mode_name}'.")


    def _validate_specific_params(self, settings: dict, click_type_for_error: str) -> dict | None:
        """Validates a single set of parameters (left or right)."""
        try:
            params = {
                'peak_cps': float(settings['peak_cps']),
                'timing_rand_ms': int(settings['timing_rand_ms']),
                'jitter_px': int(settings['jitter_px']),
                'mode': settings['mode']
                # 'mouse_button_pref' is now 'active_config' at the global level
            }
            if params['peak_cps'] <=0: raise ValueError(f"{click_type_for_error} CPS pozitif olmalı.")
            if params['timing_rand_ms'] < 0: raise ValueError(f"{click_type_for_error} Zamanlama rastgeleliği negatif olamaz.")
            if params['jitter_px'] < 0: raise ValueError(f"{click_type_for_error} Jitter yoğunluğu negatif olamaz.")

            if params['mode'] == 'Patlama':
                params['burst_duration'] = float(settings['burst_duration'])
                if params['burst_duration'] <= 0: raise ValueError(f"{click_type_for_error} Patlama süresi pozitif olmalı.")
            elif params['mode'] == 'Rastgele Aralık':
                params['min_cps_random'] = float(settings['min_cps_random'])
                params['max_cps_random'] = float(settings['max_cps_random'])
                if params['min_cps_random'] <= 0 or params['max_cps_random'] <= 0:
                    raise ValueError(f"{click_type_for_error} Rastgele Aralık CPS değerleri pozitif olmalı.")
                if params['min_cps_random'] > params['max_cps_random']:
                    raise ValueError(f"{click_type_for_error} Min CPS, Max CPS'den büyük olamaz.")
            elif params['mode'] == 'Pattern (Desen)':
                params['click_pattern'] = settings['click_pattern']
                if not params['click_pattern'].strip():
                    raise ValueError(f"{click_type_for_error} Pattern boş olamaz.")
            return params
        except (ValueError, TypeError) as e:
            self.ui.update_status_display(STATUS_ERROR, COLOR_RED, self.is_running)
            self.ui.show_error(f"{click_type_for_error} Geçersiz Girdi", f"Lütfen ayarları kontrol edin.\nHata: {e}")
            return None

    def _get_validated_params(self) -> dict | None:
        """Validates UI settings based on the active_config and returns them or None."""
        all_settings = self.ui.get_current_settings()
        active_config = all_settings['active_config']
        validated_params = {'active_config': active_config, 'left': None, 'right': None}

        if active_config == "Use Left Click Settings" or active_config == "Use Both Settings":
            left_params = self._validate_specific_params(all_settings['left'], "Sol Tık")
            if not left_params: return None
            validated_params['left'] = left_params

        if active_config == "Use Right Click Settings" or active_config == "Use Both Settings":
            right_params = self._validate_specific_params(all_settings['right'], "Sağ Tık")
            if not right_params: return None
            validated_params['right'] = right_params

        if active_config == "Use Both Settings" and (not validated_params['left'] or not validated_params['right']):
            # This case should ideally be caught by individual validations, but as a safeguard:
            self.ui.show_error("Hata", "Her iki tıklama ayarı da 'Use Both Settings' için geçerli olmalıdır.")
            return None
        if active_config == "Use Left Click Settings" and not validated_params['left']:
             return None # Error already shown by _validate_specific_params
        if active_config == "Use Right Click Settings" and not validated_params['right']:
             return None # Error already shown

        return validated_params


    def _set_program_state(self, running: bool):
        self.is_running = running
        status_text = ""
        color = COLOR_BLACK

        if running:
            color = COLOR_GREEN
            active_config = self.active_click_params.get('active_config', "")
            if active_config == "Use Left Click Settings":
                status_text = "Durum: SOL TIK ÇALIŞIYOR"
            elif active_config == "Use Right Click Settings":
                status_text = "Durum: SAĞ TIK ÇALIŞIYOR"
            elif active_config == "Use Both Settings":
                status_text = "Durum: SOL VE SAĞ TIK ÇALIŞIYOR"
            else: # Fallback, though should ideally not be reached if params are validated
                status_text = STATUS_RUNNING
        else:
            status_text = STATUS_STOPPED if self.click_thread and self.click_thread.is_alive() else STATUS_IDLE
            # Check if click_thread is None or not alive for STATUS_IDLE vs STATUS_STOPPED
            # self.click_thread is set to None when it finishes or is never started.
            # If stop_clicking is called, thread might still be alive for a moment.
            # A more robust way might be to check if it was ever started and now is_running is false.
            # For simplicity, this check is okay.
            if not self.click_thread or not self.click_thread.is_alive():
                 # If thread is None or not alive, and we are setting state to not running,
                 # it means it was either never started (IDLE) or has finished (so effectively IDLE for next start).
                 # However, if stop_clicking() was just called, self.is_running is False, but thread might be finishing.
                 # The current logic: if thread exists, it's STOPPED, else IDLE.
                 status_text = STATUS_IDLE # Let's refine: if not running, and thread is None or done, it's IDLE.
                 if self.click_thread and self.click_thread.is_alive(): # This state is transient
                     status_text = STATUS_STOPPED
                 elif self.click_thread is not None and not self.click_thread.is_alive(): # Thread has finished
                      status_text = STATUS_STOPPED # After running, it's stopped
                      # self.click_thread = None # Clean up thread object once it's done
                 # This part becomes tricky. Let's simplify:
                 # If running is false:
                 # If a click_thread object exists (even if finishing): Durduruldu
                 # If no click_thread object (never run or finished and cleaned): Beklemede
            if self.click_thread is None: # Never started or fully stopped and cleaned
                 status_text = STATUS_IDLE
            else: # Has run or is running and told to stop
                 status_text = STATUS_STOPPED


        self.ui.update_status_display(status_text, color, self.is_running)

    def start_clicking(self):
        if self.is_running: return
        if not self.trigger_input: # Changed from trigger_key
            self.ui.show_warning("Hata", "Lütfen önce bir tetikleyici atayın (tuş veya fare)!")
            return

        self.active_click_params = self._get_validated_params()
        if not self.active_click_params: return

        # Reset relevant click modes
        if self.active_click_params.get('left') and self.left_click_mode:
            self.left_click_mode.reset()
        if self.active_click_params.get('right') and self.right_click_mode:
            self.right_click_mode.reset()

        if (self.active_click_params['active_config'] == "Use Left Click Settings" and not self.left_click_mode) or \
           (self.active_click_params['active_config'] == "Use Right Click Settings" and not self.right_click_mode) or \
           (self.active_click_params['active_config'] == "Use Both Settings" and (not self.left_click_mode or not self.right_click_mode)):
            self.ui.show_error("Hata", "Aktif tıklama için mod(lar) seçilemedi/yüklenemedi.")
            return

        self.click_count = 0
        self.ui.update_click_count(self.click_count)
        self._set_program_state(True)
        self._stop_requested_after_cycle = False

        self.click_thread = threading.Thread(target=self._click_loop, daemon=True)
        self.click_thread.start()

    def _click_loop(self):
        start_time = time.time()
        # For "Use Both Settings", keep track of which click is next
        next_click_is_left = True
        # Timers for independent CPS when 'Both' is active. Not perfectly independent yet with single loop.
        # This is a simplified approach. True independent timing would need separate threads or more complex async logic.
        last_left_click_time = start_time
        last_right_click_time = start_time

        while self.is_running:
            if self._stop_requested_after_cycle:
                self.ui.after(0, self.stop_clicking)
                break

            try:
                current_time = time.time()
                elapsed_total_time = current_time - start_time

                active_config = self.active_click_params['active_config']

                params_to_use = None
                click_mode_to_use = None
                button_to_press = None
                time_since_last_of_type = 0

                if active_config == "Use Left Click Settings":
                    params_to_use = self.active_click_params['left']
                    click_mode_to_use = self.left_click_mode
                    button_to_press = 'left'
                    time_since_last_of_type = elapsed_total_time # Simplified for single click type
                elif active_config == "Use Right Click Settings":
                    params_to_use = self.active_click_params['right']
                    click_mode_to_use = self.right_click_mode
                    button_to_press = 'right'
                    time_since_last_of_type = elapsed_total_time # Simplified
                elif active_config == "Use Both Settings":
                    if next_click_is_left:
                        params_to_use = self.active_click_params['left']
                        click_mode_to_use = self.left_click_mode
                        button_to_press = 'left'
                        time_since_last_of_type = current_time - last_left_click_time
                    else:
                        params_to_use = self.active_click_params['right']
                        click_mode_to_use = self.right_click_mode
                        button_to_press = 'right'
                        time_since_last_of_type = current_time - last_right_click_time
                else: # Should not happen
                    self.ui.after(0, self.stop_clicking)
                    break

                if not params_to_use or not click_mode_to_use:
                    print("Error: Params or click mode not available in loop.")
                    self.ui.after(0, self.stop_clicking)
                    break

                current_cps, jitter_x, jitter_y, _ = click_mode_to_use.get_next_action(params_to_use, time_since_last_of_type)

                if current_cps <= 0:
                    if self.is_running: self.ui.after(0, self.stop_clicking)
                    break

                current_cps = max(0.1, current_cps)

                # Determine click_type_str for UI update
                click_type_str = ""
                if active_config == "Use Left Click Settings":
                    click_type_str = "Sol"
                elif active_config == "Use Right Click Settings":
                    click_type_str = "Sağ"
                elif active_config == "Use Both Settings":
                    click_type_str = "Sol" if button_to_press == 'left' else "Sağ"

                self.ui.after(0, self.ui.update_realtime_cps, current_cps, click_type_str)


                pos = pyautogui.position()
                pyautogui.click(x=pos.x + int(jitter_x), y=pos.y + int(jitter_y), button=button_to_press)

                self.click_count += 1
                self.ui.after(0, self.ui.update_click_count, self.click_count)

                # Update last click time for the type just performed
                if active_config == "Use Both Settings":
                    if button_to_press == 'left':
                        last_left_click_time = current_time
                    else:
                        last_right_click_time = current_time
                    next_click_is_left = not next_click_is_left # Alternate for next iteration

                base_delay = 1.0 / current_cps
                rand_delay_ms = params_to_use['timing_rand_ms']
                rand_delay_s = random.uniform(-rand_delay_ms / 1000.0, rand_delay_ms / 1000.0)
                actual_delay = max(0.001, base_delay + rand_delay_s)

                # If "Both" are active, the delay should ideally be managed to respect both CPS.
                # This simplified alternating approach uses the delay of the *current* click performed.
                # A more advanced system might calculate delays to interleave based on individual target CPS.

                target_time = time.perf_counter() + actual_delay
                while time.perf_counter() < target_time:
                    if not self.is_running: break

                if hasattr(click_mode_to_use, 'time_counter') and isinstance(click_mode_to_use.time_counter, float):
                    if current_cps > 0: click_mode_to_use.time_counter += actual_delay * 0.5

            except Exception as e:
                print(f"Click Loop Hatası: {e}")
                self.ui.after(0, self.stop_clicking) # Ensure UI updates on main thread
                break
        # Ensure state is updated if loop exits unexpectedly
        if self.is_running: # Check if still running before attempting to update UI
            self.ui.after(0, self._set_program_state, False)
        self.ui.after(0, self._handle_thread_completion) # Ensure cleanup


    def _handle_thread_completion(self):
        """Called when the click_thread finishes."""
        # Check if the thread object exists and is the one that just finished
        if self.click_thread is not None and not self.click_thread.is_alive():
            self.click_thread = None
        # Re-evaluate program state, which might transition to IDLE if not already
        if not self.is_running: # Ensure is_running is indeed false
            self._set_program_state(False)


    def stop_clicking(self):
        if not self.is_running: return
        self._set_program_state(False) # This sets self.is_running to False
        # The click_thread will see self.is_running is False and exit.
        # _handle_thread_completion will then be called.

    def stop_clicking_after_current_cycle(self):
        self._stop_requested_after_cycle = True

    def toggle_clicking(self):
        if self.is_running:
            self.stop_clicking()
        else:
            self.start_clicking()

    def set_assign_mode(self):
        self.is_assigning_key = True
        self.ui.update_trigger_key_display(ASSIGN_KEY_PROMPT, False)
        # Focus stealing might be an issue for pynput if Tkinter window is not focused.
        # Usually, pynput listeners are global.

    def _format_input_name(self, input_obj) -> str:
        if isinstance(input_obj, keyboard.Key):
            return input_obj.name.upper()
        elif isinstance(input_obj, keyboard.KeyCode):
            return input_obj.char.upper() if input_obj.char else "UNKNOWN_KEY"
        elif isinstance(input_obj, mouse.Button):
            return f"MOUSE_{input_obj.name.upper()}"
        return "ATANMADI" # Fallback

    def _assign_input(self, input_obj):
        if not self.is_assigning_key: return

        # Check for ESC key to cancel assignment
        if isinstance(input_obj, keyboard.Key) and input_obj == keyboard.Key.esc:
            self.is_assigning_key = False # Must do this before updating display
            if self.trigger_input:
                self.ui.update_trigger_key_display(self._format_input_name(self.trigger_input), True)
            else:
                self.ui.update_trigger_key_display(KEY_NOT_ASSIGNED, False)
            return

        self.trigger_input = input_obj
        self.is_assigning_key = False # Assignment done
        self.ui.update_trigger_key_display(self._format_input_name(self.trigger_input), True)


    def _start_listeners(self):
        # Keyboard listener
        key_listener = keyboard.Listener(on_press=self._on_key_press_event)
        key_listener.daemon = True
        key_listener.start()
        # Mouse listener (for trigger assignment and potentially other functions later)
        # We only care about clicks for assignment/trigger, not move or scroll for now.
        mouse_listener = mouse.Listener(on_click=self._on_mouse_click_event)
        mouse_listener.daemon = True
        mouse_listener.start()

    def _on_key_press_event(self, key):
        # Using self.ui.after to ensure Tkinter calls are made from the main thread
        if key == keyboard.Key.f12:
            self.ui.after(0, self.emergency_shutdown)
            return

        if self.is_assigning_key:
            self.ui.after(0, self._assign_input, key)
        elif self.trigger_input and self.trigger_input == key:
            self.ui.after(0, self.toggle_clicking)

    def _on_mouse_click_event(self, x, y, button, pressed):
        # We only care about button presses for assignment or trigger
        if not pressed:
            return

        # Using self.ui.after for Tkinter thread safety
        if self.is_assigning_key:
            self.ui.after(0, self._assign_input, button)
        elif self.trigger_input and self.trigger_input == button:
            self.ui.after(0, self.toggle_clicking)

    # Note: _process_key_event is effectively merged into _on_key_press_event and _on_mouse_click_event

    def emergency_shutdown(self):
        print("Acil Durum Kapatma... Program sonlandırılıyor...")
        self.is_running = False
        if self.click_thread and self.click_thread.is_alive():
            # Attempt to signal thread to stop; it should check self.is_running
            # Forcibly stopping threads is generally unsafe, rely on the loop condition
            pass
        if self.ui:
            # Safely destroy UI from main thread if possible, or just exit
            try:
                self.ui.destroy()
            except tk.TclError: # Can happen if already destroying or from wrong thread
                pass
        sys.exit()

    def run(self):
        try:
            self.ui.mainloop()
        except KeyboardInterrupt:
            print("Program kullanıcı tarafından sonlandırıldı.")
            self.emergency_shutdown()
        finally:
            # Ensure listeners are stopped if mainloop exits unexpectedly
            # Daemon threads should stop automatically, but explicit cleanup can be added if needed
            pass


if __name__ == "__main__":
    core_app = AppCore()
    core_app.run()
