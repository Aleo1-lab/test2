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
        self.is_running = False # Will represent if ANY clicking is active
        self.click_thread = None
        
        self.left_trigger_input = None
        self.right_trigger_input = None
        
        self.assigning_for_left = False # True if currently assigning for left trigger
        self.assigning_for_right = False # True if currently assigning for right trigger
        # self.is_assigning_key can be removed or repurposed if we ensure only one assignment happens at a time.
        # For now, let's keep it simple: only one can be true: assigning_for_left or assigning_for_right.

        self.is_left_clicking = False
        self.is_right_clicking = False

        self.click_count = 0
        self._stop_requested_after_cycle = False # This might need per-click-type handling later

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
        # ui_widgets access removed here to prevent AttributeError during init
        try:
            new_mode_instance = get_click_mode(mode_name, self) # Pass self (AppCore)
        except ValueError as e:
            # Error is shown by UI if it's already initialized,
            # otherwise AppCore just logs it or fails to set the mode.
            # self.ui might not be fully available here yet.
            print(f"Error loading mode {mode_name} for {click_type}: {e}")
            # Attempt to load fallback mode directly without UI interaction from AppCore
            try:
                new_mode_instance = get_click_mode("Sabit", self)
                print(f"Fallback to 'Sabit' mode for {click_type} due to error.")
            except ValueError:
                print(f"APPCORE_CRITICAL: Fallback mode 'Sabit' for {click_type} also failed.")
                # new_mode_instance remains None

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

    def _validate_and_store_params(self, click_type_to_validate: str) -> bool:
        """Validates parameters for a specific click type ('left' or 'right') and stores them.
        Returns True if validation is successful, False otherwise.
        """
        all_settings = self.ui.get_current_settings() # Contains 'left' and 'right' keys
        
        if click_type_to_validate == 'left':
            params = self._validate_specific_params(all_settings['left'], "Sol Tık")
            if not params:
                # Potentially stop left clicking if it was running with invalid new params
                if self.is_left_clicking: self.toggle_left_click() # This might need refinement
                return False
            self.active_click_params['left'] = params
            if self.left_click_mode: self.left_click_mode.reset()
            return True
        elif click_type_to_validate == 'right':
            params = self._validate_specific_params(all_settings['right'], "Sağ Tık")
            if not params:
                # Potentially stop right clicking
                if self.is_right_clicking: self.toggle_right_click()
                return False
            self.active_click_params['right'] = params
            if self.right_click_mode: self.right_click_mode.reset()
            return True
        return False

    # _get_validated_params is removed, replaced by _validate_and_store_params for specific types


    def _update_global_state_and_ui(self):
        """Updates self.is_running and UI status based on is_left_clicking and is_right_clicking."""
        self.is_running = self.is_left_clicking or self.is_right_clicking
        
        status_text = STATUS_IDLE
        color = COLOR_BLACK

        if self.is_left_clicking and self.is_right_clicking:
            status_text = "Durum: SOL & SAĞ TIK AKTİF"
            color = COLOR_GREEN
        elif self.is_left_clicking:
            status_text = "Durum: SOL TIK AKTİF"
            color = COLOR_GREEN
        elif self.is_right_clicking:
            status_text = "Durum: SAĞ TIK AKTİF"
            color = COLOR_GREEN
        else: # Neither is clicking
            if self.click_thread and self.click_thread.is_alive():
                # This case should ideally not be common if thread stops when no clicks are active
                status_text = STATUS_STOPPED 
            else:
                status_text = STATUS_IDLE
                self.click_thread = None # Ensure thread is cleaned up if it finished

        # The 'is_running' for update_status_display now means "are settings changeable"
        # Settings should be changeable if neither is clicking (effectively, if global self.is_running is false)
        self.ui.update_status_display(status_text, color, self.is_running)


    def _set_program_state(self, running: bool): # This method is now less central, replaced by _update_global_state_and_ui
        # Kept for compatibility if any old call remains, but should be phased out.
        # For now, let it call the new central status update.
        self._update_global_state_and_ui()

    def toggle_left_click(self):
        if not self.is_left_clicking: # Try to start left clicking
            if not self.left_trigger_input:
                self.ui.show_warning("Uyarı", "Sol tıklama için tetikleyici atanmamış.")
                return
            if not self._validate_and_store_params('left'):
                # Error already shown by _validate_and_store_params
                return
            if not self.left_click_mode:
                self.ui.show_error("Hata", "Sol tıklama için mod yüklenemedi.")
                return
            
            self.is_left_clicking = True
            self.left_click_mode.reset() # Ensure mode is reset before starting
            self.click_count = 0 # Reset click count when starting any click type? Or keep global?
                                 # For now, let's reset it if nothing else is running.
            if not self.is_right_clicking:
                self.click_count = 0 
            self.ui.update_click_count(self.click_count)

        else: # Stop left clicking
            self.is_left_clicking = False
        
        self._manage_click_thread()
        self._update_global_state_and_ui()

    def toggle_right_click(self):
        if not self.is_right_clicking: # Try to start right clicking
            if not self.right_trigger_input:
                self.ui.show_warning("Uyarı", "Sağ tıklama için tetikleyici atanmamış.")
                return
            if not self._validate_and_store_params('right'):
                return
            if not self.right_click_mode:
                self.ui.show_error("Hata", "Sağ tıklama için mod yüklenemedi.")
                return

            self.is_right_clicking = True
            self.right_click_mode.reset()
            if not self.is_left_clicking: # Reset count if only this one is starting
                self.click_count = 0
            self.ui.update_click_count(self.click_count)

        else: # Stop right clicking
            self.is_right_clicking = False

        self._manage_click_thread()
        self._update_global_state_and_ui()

    def _manage_click_thread(self):
        """Starts or stops the click_thread based on is_left_clicking or is_right_clicking."""
        should_be_running = self.is_left_clicking or self.is_right_clicking

        if should_be_running and (not self.click_thread or not self.click_thread.is_alive()):
            # Start thread
            self._stop_requested_after_cycle = False # Reset this flag
            self.click_thread = threading.Thread(target=self._click_loop, daemon=True)
            self.click_thread.start()
        elif not should_be_running and self.click_thread and self.click_thread.is_alive():
            # Signal thread to stop (it will stop by checking is_left_clicking/is_right_clicking)
            # The _click_loop itself needs to handle its exit condition based on these flags.
            # self.is_running (global) will be false, which _click_loop already checks.
            pass # Loop will terminate based on is_left_clicking and is_right_clicking being false.

    # Old start_clicking, stop_clicking, toggle_clicking are effectively replaced by
    # toggle_left_click, toggle_right_click and _manage_click_thread.
    # Keep them for a bit if other parts call them, but they should be removed.

    def start_clicking(self): # Old method - DEPRECATED
        # This could be re-purposed to "start both if triggers assigned", or removed.
        # For now, make it do nothing or log a warning.
        print("Deprecated: start_clicking() called. Use specific trigger.")
        pass

    def stop_clicking(self): # Old method - DEPRECATED
        # This could be "stop all".
        self.is_left_clicking = False
        self.is_right_clicking = False
        self._manage_click_thread() # This will signal the thread to stop if it's running.
        self._update_global_state_and_ui() # Update UI

    def toggle_clicking(self): # Old method - DEPRECATED
        print("Deprecated: toggle_clicking() called. Use specific triggers.")
        # Could toggle both if both are configured? Or prefer left? For now, ambiguous.
        # If only one is active, toggle that one. If both, toggle both off?
        # Better to rely on specific toggles for now.
        pass


    # def _set_program_state(self, running: bool): # OLD METHOD - TO BE REPLACED/REMOVED
    #     self.is_running = running
    #     status_text = ""
    #     color = COLOR_BLACK

    #     if running:
    #         color = COLOR_GREEN
    #         active_config = self.active_click_params.get('active_config', "") # active_config no longer exists
    #         if active_config == "Use Left Click Settings":
    #             status_text = "Durum: SOL TIK ÇALIŞIYOR"
    #         elif active_config == "Use Right Click Settings":
    #             status_text = "Durum: SAĞ TIK ÇALIŞIYOR"
    #         elif active_config == "Use Both Settings":
    #             status_text = "Durum: SOL VE SAĞ TIK ÇALIŞIYOR"
    #         else: # Fallback, though should ideally not be reached if params are validated
    #             status_text = STATUS_RUNNING
    #     else:
    #         status_text = STATUS_STOPPED if self.click_thread and self.click_thread.is_alive() else STATUS_IDLE
    #         # Check if click_thread is None or not alive for STATUS_IDLE vs STATUS_STOPPED
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
        initial_time = time.time()
        next_left_click_due_time = initial_time
        next_right_click_due_time = initial_time
        
        # Keep track of last actual click times for time_since_last_of_type calculation for modes
        # Initialize with loop start to avoid issues on first click for a type
        self._last_actual_left_click_time = initial_time 
        self._last_actual_right_click_time = initial_time

        # self.is_running is the global flag updated by _manage_click_thread and _update_global_state_and_ui
        # It reflects if EITHER left or right clicking is active.
        while self.is_running: # Loop as long as any click type is supposed to be active
            if self._stop_requested_after_cycle: # This flag might need to be per click type if we reintroduce it
                self.is_left_clicking = False
                self.is_right_clicking = False
                # self.ui.after(0, self.stop_clicking) # stop_clicking will update UI and thread management
                # Let the loop terminate naturally by is_running becoming false
                break 
            
            try:
                current_time = time.time()
                executed_click_this_cycle = False

                # Process Left Click
                if self.is_left_clicking and current_time >= next_left_click_due_time:
                    if 'left' not in self.active_click_params or not self.left_click_mode:
                        print("Left click params or mode not ready, stopping left click.")
                        self.is_left_clicking = False # Stop this type
                        # self.ui.after(0, self.toggle_left_click) # This might cause issues if called from thread
                        self.ui.after(0, self._update_global_state_and_ui) # Update UI
                        if not self.is_right_clicking: break # Exit loop if nothing else is active
                        continue # Try right click or sleep

                    params = self.active_click_params['left']
                    mode = self.left_click_mode
                    time_since_last = current_time - self._last_actual_left_click_time

                    current_cps, jitter_x, jitter_y, _ = mode.get_next_action(params, time_since_last)

                    if current_cps <= 0:
                        self.is_left_clicking = False
                        self.ui.after(0, self._update_global_state_and_ui)
                        if not self.is_right_clicking: break
                        continue
                    
                    current_cps = max(0.1, current_cps)
                    self.ui.after(0, self.ui.update_realtime_cps, current_cps, "Sol")
                    
                    pos = pyautogui.position()
                    pyautogui.click(x=pos.x + int(jitter_x), y=pos.y + int(jitter_y), button='left')
                    
                    self.click_count += 1
                    self.ui.after(0, self.ui.update_click_count, self.click_count)
                    
                    base_delay = 1.0 / current_cps
                    rand_delay_ms = params['timing_rand_ms']
                    rand_delay_s = random.uniform(-rand_delay_ms / 1000.0, rand_delay_ms / 1000.0)
                    actual_delay = max(0.001, base_delay + rand_delay_s)
                    
                    next_left_click_due_time = current_time + actual_delay
                    self._last_actual_left_click_time = current_time
                    executed_click_this_cycle = True
                    if hasattr(mode, 'time_counter'): mode.time_counter += actual_delay

                # Process Right Click (independent of left click)
                if self.is_right_clicking and current_time >= next_right_click_due_time:
                    if 'right' not in self.active_click_params or not self.right_click_mode:
                        print("Right click params or mode not ready, stopping right click.")
                        self.is_right_clicking = False
                        self.ui.after(0, self._update_global_state_and_ui)
                        if not self.is_left_clicking: break
                        continue

                    params = self.active_click_params['right']
                    mode = self.right_click_mode
                    time_since_last = current_time - self._last_actual_right_click_time

                    current_cps, jitter_x, jitter_y, _ = mode.get_next_action(params, time_since_last)

                    if current_cps <= 0:
                        self.is_right_clicking = False
                        self.ui.after(0, self._update_global_state_and_ui)
                        if not self.is_left_clicking: break
                        continue

                    current_cps = max(0.1, current_cps)
                    self.ui.after(0, self.ui.update_realtime_cps, current_cps, "Sağ")

                    pos = pyautogui.position()
                    pyautogui.click(x=pos.x + int(jitter_x), y=pos.y + int(jitter_y), button='right')

                    self.click_count += 1
                    self.ui.after(0, self.ui.update_click_count, self.click_count)

                    base_delay = 1.0 / current_cps
                    rand_delay_ms = params['timing_rand_ms']
                    rand_delay_s = random.uniform(-rand_delay_ms / 1000.0, rand_delay_ms / 1000.0)
                    actual_delay = max(0.001, base_delay + rand_delay_s)

                    next_right_click_due_time = current_time + actual_delay
                    self._last_actual_right_click_time = current_time
                    executed_click_this_cycle = True
                    if hasattr(mode, 'time_counter'): mode.time_counter += actual_delay
                
                # Check if self.is_running became false due to external stop or error
                if not (self.is_left_clicking or self.is_right_clicking):
                    self.is_running = False # Ensure global flag is also false
                    break 

                # Sleep management
                if not executed_click_this_cycle:
                    # No click was ready, sleep until the next one is due or a short interval
                    sleep_target = float('inf')
                    if self.is_left_clicking:
                        sleep_target = min(sleep_target, next_left_click_due_time)
                    if self.is_right_clicking:
                        sleep_target = min(sleep_target, next_right_click_due_time)
                    
                    sleep_duration = max(0, sleep_target - time.time())
                    # Sleep for a short, responsive duration, but not excessively long if one click type is very slow
                    time.sleep(min(max(0.001, sleep_duration), 0.01)) # Max sleep of 10ms if no click, min 1ms
                else:
                    # A click was performed, short sleep to yield and allow quick check for other type
                    time.sleep(0.001) 

            except Exception as e:
                print(f"Click Loop Hatası: {e}")
                self.ui.after(0, lambda: self.ui.show_error("Döngü Hatası", f"Tıklama döngüsünde hata: {e}"))
                self.is_left_clicking = False # Stop all on error
                self.is_right_clicking = False
                self.is_running = False # Ensure loop terminates
                break # Exit loop
        
        # Loop finished (either normally or due to error/stop)
        self.is_running = False # Explicitly set to false
        self.ui.after(0, self._update_global_state_and_ui) # Final UI update from main thread
        self.ui.after(0, self._handle_thread_completion)


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
            self.stop_clicking() # This will need to be updated for dual triggers
        else:
            self.start_clicking() # This will need to be updated for dual triggers

    def set_assign_mode(self, trigger_type: str):
        # Cancel any other ongoing assignment
        self.assigning_for_left = False
        self.assigning_for_right = False
        
        current_trigger_for_prompt = None
        if trigger_type == 'left':
            self.assigning_for_left = True
            current_trigger_for_prompt = self.left_trigger_input
            # Update other trigger label to normal if it was in prompt mode
            if self.right_trigger_input:
                 self.ui.update_trigger_key_display(self._format_input_name(self.right_trigger_input), True, 'right')
            else:
                 self.ui.update_trigger_key_display(KEY_NOT_ASSIGNED, False, 'right')
        elif trigger_type == 'right':
            self.assigning_for_right = True
            current_trigger_for_prompt = self.right_trigger_input
            # Update other trigger label to normal
            if self.left_trigger_input:
                self.ui.update_trigger_key_display(self._format_input_name(self.left_trigger_input), True, 'left')
            else:
                self.ui.update_trigger_key_display(KEY_NOT_ASSIGNED, False, 'left')
        else:
            return # Invalid type

        # Update the target trigger label to show "Assigning..."
        self.ui.update_trigger_key_display(ASSIGN_KEY_PROMPT, False, trigger_type)

    def _format_input_name(self, input_obj) -> str:
        if input_obj is None: # Handle case where trigger is not set
            return KEY_NOT_ASSIGNED
        if isinstance(input_obj, keyboard.Key):
            return input_obj.name.upper()
        elif isinstance(input_obj, keyboard.KeyCode):
            return input_obj.char.upper() if input_obj.char else "UNKNOWN_KEY"
        elif isinstance(input_obj, mouse.Button):
            return f"MOUSE_{input_obj.name.upper()}"
        return "ATANMADI" # Fallback

    def _assign_input(self, input_obj):
        assign_type = None
        if self.assigning_for_left:
            assign_type = 'left'
        elif self.assigning_for_right:
            assign_type = 'right'
        else:
            return # Not in assignment mode

        # Check for ESC key to cancel assignment
        if isinstance(input_obj, keyboard.Key) and input_obj == keyboard.Key.esc:
            self.assigning_for_left = False
            self.assigning_for_right = False
            current_trigger = None
            if assign_type == 'left':
                current_trigger = self.left_trigger_input
            else: # right
                current_trigger = self.right_trigger_input
            
            self.ui.update_trigger_key_display(self._format_input_name(current_trigger), current_trigger is not None, assign_type)
            return

        if assign_type == 'left':
            self.left_trigger_input = input_obj
            self.assigning_for_left = False
            self.ui.update_trigger_key_display(self._format_input_name(self.left_trigger_input), True, 'left')
        elif assign_type == 'right':
            self.right_trigger_input = input_obj
            self.assigning_for_right = False
            self.ui.update_trigger_key_display(self._format_input_name(self.right_trigger_input), True, 'right')


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

        if self.assigning_for_left or self.assigning_for_right: # Check new assignment flags
            self.ui.after(0, self._assign_input, key)
        elif self.left_trigger_input and self.left_trigger_input == key:
            self.ui.after(0, self.toggle_left_click)
        elif self.right_trigger_input and self.right_trigger_input == key:
            self.ui.after(0, self.toggle_right_click)

    def _on_mouse_click_event(self, x, y, button, pressed):
        # We only care about button presses for assignment or trigger
        if not pressed:
            return

        # Using self.ui.after for Tkinter thread safety
        if self.assigning_for_left or self.assigning_for_right: # Check new assignment flags
            self.ui.after(0, self._assign_input, button)
        elif self.left_trigger_input and self.left_trigger_input == button:
            self.ui.after(0, self.toggle_left_click)
        elif self.right_trigger_input and self.right_trigger_input == button:
            self.ui.after(0, self.toggle_right_click)

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
