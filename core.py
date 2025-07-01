"""
Core application logic for the Gelişmiş Otomatik Tıklayıcı.

Handles UI interactions, click event generation, state management,
and communication between the UI and click modes.
"""
import pyautogui
pyautogui.PAUSE = 0  # Minimal pause between pyautogui actions
pyautogui.FAILSAFE = False  # Disable failsafe (moving mouse to corner to stop)

import threading
import time
import random
import sys
from pynput import keyboard, mouse

from ui import (AutoClickerUI, STATUS_IDLE, STATUS_STOPPED,
                STATUS_ERROR, ASSIGN_KEY_PROMPT, KEY_NOT_ASSIGNED,
                COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_BLACK) # STATUS_RUNNING removed as it's dynamic
from click_modes import get_click_mode, ClickMode # Added ClickMode for type hint

class AppCore:
    """
    Manages the application's core functionalities including UI interaction,
    click generation, state, and input listeners.
    """
    def __init__(self):
        self.ui: AutoClickerUI = AutoClickerUI(self)
        self.is_running: bool = False  # True if any click type (left/right) is active
        self.click_thread: threading.Thread | None = None
        
        self.left_trigger_input: keyboard.Key | keyboard.KeyCode | mouse.Button | None = None
        self.right_trigger_input: keyboard.Key | keyboard.KeyCode | mouse.Button | None = None
        
        self.assigning_for_left: bool = False
        self.assigning_for_right: bool = False

        self.is_left_clicking: bool = False
        self.is_right_clicking: bool = False

        self.click_count: int = 0
        self._stop_requested_after_cycle: bool = False

        self.left_click_mode: ClickMode | None = None
        self.right_click_mode: ClickMode | None = None
        self.active_click_params: dict = {} # Holds validated params for 'left' and 'right'

        self._start_listeners()
        # Click modes (left_click_mode, right_click_mode) are initialized
        # by the UI's __init__ which calls self.on_mode_changed.

    def on_mode_changed(self, mode_name: str, click_type: str) -> None:
        """
        Handles changes in click mode selection from the UI for 'left' or 'right' clicks.
        Loads the new mode and resets it.
        """
        new_mode_instance: ClickMode | None = None
        try:
            new_mode_instance = get_click_mode(mode_name, self)
        except ValueError as e:
            print(f"Error loading mode '{mode_name}' for {click_type} click: {e}")
            try:
                # Attempt to load a default fallback mode
                new_mode_instance = get_click_mode("Sabit", self)
                print(f"Fallback to 'Sabit' mode for {click_type} click due to error.")
                # The UI should ideally also reflect this fallback if it initiated the change.
            except ValueError: # Should not happen if "Sabit" mode is always present
                print(f"APPCORE_CRITICAL: Fallback mode 'Sabit' for {click_type} also failed.")

        if click_type == 'left':
            self.left_click_mode = new_mode_instance
            if self.left_click_mode:
                self.left_click_mode.reset()
        elif click_type == 'right':
            self.right_click_mode = new_mode_instance
            if self.right_click_mode:
                self.right_click_mode.reset()

        if not new_mode_instance:
            print(f"APPCORE_WARNING: No click mode instance was set for {click_type} (mode name: '{mode_name}').")

    def _validate_specific_params(self, settings: dict, click_type_for_error: str) -> dict | None:
        """
        Validates parameters for a single click type (e.g., 'left' or 'right').

        Args:
            settings (dict): The raw settings dictionary for the click type from the UI.
            click_type_for_error (str): A string like "Sol Tık" for error messages.

        Returns:
            dict | None: A dictionary of validated parameters, or None if validation fails.
        """
        try:
            params = {
                'peak_cps': float(settings['peak_cps']),
                'timing_rand_ms': int(settings['timing_rand_ms']),
                'jitter_px': int(settings['jitter_px']),
                'mode': settings['mode'] # Mode name string
            }
            # Basic range checks for common parameters
            if not (0 < params['peak_cps'] <= 1000): # Max 1000 CPS as a sanity check
                raise ValueError("CPS değeri pozitif ve makul bir aralıkta olmalı (örn: 1-1000).")
            if not (0 <= params['timing_rand_ms'] <= 1000): # Max 1s randomness
                raise ValueError("Zamanlama rastgeleliği 0-1000ms aralığında olmalı.")
            if not (0 <= params['jitter_px'] <= 100): # Max 100px jitter
                 raise ValueError("Jitter yoğunluğu 0-100px aralığında olmalı.")

            current_mode_name = params['mode']
            if current_mode_name == 'Patlama':
                params['burst_duration'] = float(settings['burst_duration'])
                if not (0 < params['burst_duration'] <= 300): # Max 5 mins burst duration
                    raise ValueError("Patlama süresi pozitif ve makul olmalı (örn: 1-300sn).")
            elif current_mode_name == 'Rastgele Aralık':
                params['min_cps_random'] = float(settings['min_cps_random'])
                params['max_cps_random'] = float(settings['max_cps_random'])
                if not (0 < params['min_cps_random'] <= 1000 and 0 < params['max_cps_random'] <= 1000):
                    raise ValueError("Rastgele Aralık CPS değerleri pozitif ve makul olmalı.")
                if params['min_cps_random'] > params['max_cps_random']:
                    raise ValueError("Min CPS, Max CPS'den büyük olamaz.")
            elif current_mode_name == 'Pattern (Desen)':
                params['click_pattern'] = settings['click_pattern']
                if not params['click_pattern'].strip(): # Check if pattern is not just whitespace
                    raise ValueError("Pattern boş olamaz.")
            return params
        except (ValueError, TypeError, KeyError) as e:
            error_message = f"Lütfen {click_type_for_error} ayarlarını kontrol edin.\nHata: {e}"
            if hasattr(self, 'ui') and self.ui: # Ensure UI is available
                self.ui.update_status_display(STATUS_ERROR, COLOR_RED, self.is_running)
                self.ui.show_error(f"{click_type_for_error} Geçersiz Girdi", error_message)
            else: # Fallback if UI is not ready (e.g. very early error)
                print(f"UI_VALIDATION_ERROR for {click_type_for_error}: {error_message}")
            return None

    def _validate_and_store_params(self, click_type_to_validate: str) -> bool:
        """
        Validates parameters for a specific click type ('left' or 'right') from UI settings,
        stores them if valid, and handles UI updates/state changes on validation failure.
        """
        all_settings = self.ui.get_current_settings()
        
        specific_settings = all_settings.get(click_type_to_validate)
        if not specific_settings:
            print(f"Hata: {click_type_to_validate} için ayarlar bulunamadı (UI'dan alınamadı).")
            if hasattr(self, 'ui') and self.ui:
                self.ui.show_error("Program Hatası", f"{click_type_to_validate} için ayarlar yüklenemedi.")
            return False

        error_prefix = "Sol Tık" if click_type_to_validate == 'left' else "Sağ Tık"
        params = self._validate_specific_params(specific_settings, error_prefix)

        if not params:
            # If validation fails, stop the specific click type if it was running.
            if click_type_to_validate == 'left' and self.is_left_clicking:
                self.is_left_clicking = False
                self._manage_click_thread() # Check if main click thread needs to stop
                self._update_global_state_and_ui() # Update overall state and UI
            elif click_type_to_validate == 'right' and self.is_right_clicking:
                self.is_right_clicking = False
                self._manage_click_thread()
                self._update_global_state_and_ui()
            return False

        self.active_click_params[click_type_to_validate] = params
        # Click mode reset is handled in the toggle_..._click methods when starting.
        return True

    def _update_global_state_and_ui(self) -> None:
        """
        Updates the global 'is_running' state based on individual click states
        and refreshes the UI status display accordingly.
        """
        previously_running = self.is_running
        self.is_running = self.is_left_clicking or self.is_right_clicking
        
        status_text: str = STATUS_IDLE
        color: str = COLOR_BLACK

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
            if previously_running and not self.is_running: # Was running, now stopped by toggles/modes
                 status_text = STATUS_STOPPED
            else: # Never ran, or was already stopped and thread might have finished
                 status_text = STATUS_IDLE

            # Refine status if thread is involved
            if self.click_thread and not self.click_thread.is_alive(): # Thread just finished
                self.click_thread = None # Clean up thread object
                status_text = STATUS_IDLE # Now truly idle or stopped and thread cleaned
            elif self.click_thread and self.click_thread.is_alive() and not self.is_running:
                 # This state: we've signaled stop (is_running is false), but thread is still finishing up.
                 status_text = STATUS_STOPPED
            elif not self.is_running and not self.click_thread: # No clicks active, no thread object
                 status_text = STATUS_IDLE

        self.ui.update_status_display(status_text, color, self.is_running)

    def toggle_left_click(self) -> None:
        """Toggles the left click state (start/stop)."""
        if not self.is_left_clicking: # Attempting to start
            if not self.left_trigger_input:
                self.ui.show_warning("Uyarı", "Sol tıklama için tetikleyici atanmamış.")
                return
            if not self._validate_and_store_params('left'): # Validates and stores if successful
                return # Validation failed, error shown by _validate_and_store_params
            if not self.left_click_mode: # Should be loaded if validation passed for a mode
                self.ui.show_error("Hata", "Sol tıklama için mod yüklenemedi.")
                return
            
            self.is_left_clicking = True
            if self.left_click_mode: # Should always be true here
                self.left_click_mode.reset()

            if not self.is_right_clicking: # If this is the only click type starting now
                self.click_count = 0 
            self.ui.update_click_count(self.click_count) # Update count display
        else: # Attempting to stop
            self.is_left_clicking = False
        
        self._manage_click_thread()
        self._update_global_state_and_ui()

    def toggle_right_click(self) -> None:
        """Toggles the right click state (start/stop)."""
        if not self.is_right_clicking: # Attempting to start
            if not self.right_trigger_input:
                self.ui.show_warning("Uyarı", "Sağ tıklama için tetikleyici atanmamış.")
                return
            if not self._validate_and_store_params('right'):
                return
            if not self.right_click_mode:
                self.ui.show_error("Hata", "Sağ tıklama için mod yüklenemedi.")
                return

            self.is_right_clicking = True
            if self.right_click_mode:
                self.right_click_mode.reset()
            if not self.is_left_clicking: # If this is the only click type starting now
                self.click_count = 0
            self.ui.update_click_count(self.click_count) # Update count display
        else: # Attempting to stop
            self.is_right_clicking = False

        self._manage_click_thread()
        self._update_global_state_and_ui()

    def _manage_click_thread(self) -> None:
        """
        Manages the click thread. Starts it if any click type is active
        and the thread isn't already running. The thread stops itself
        when no click types are active.
        """
        should_be_globally_active = self.is_left_clicking or self.is_right_clicking

        if should_be_globally_active and (not self.click_thread or not self.click_thread.is_alive()):
            self._stop_requested_after_cycle = False # Reset flag when starting thread
            self.click_thread = threading.Thread(target=self._click_loop, daemon=True)
            self.click_thread.start()
        # If should_be_globally_active is False, the _click_loop's `while self.is_running`
        # condition (where self.is_running is updated by _update_global_state_and_ui)
        # will cause the thread to terminate.

    def _click_loop(self) -> None:
        """The main clicking loop executed in a separate thread."""
        initial_time = time.time()
        next_left_click_due_time: float = initial_time
        next_right_click_due_time: float = initial_time
        
        self._last_actual_left_click_time: float = initial_time
        self._last_actual_right_click_time: float = initial_time

        while self.is_running: # Relies on self.is_running being updated by UI thread via toggles
            if self._stop_requested_after_cycle:
                self.is_left_clicking = False
                self.is_right_clicking = False
                # self.is_running will be set to False by _update_global_state_and_ui, called post-loop
                break 
            
            try:
                current_time = time.time()
                executed_click_this_cycle = False

                # Process Left Click
                if self.is_left_clicking and current_time >= next_left_click_due_time:
                    if 'left' not in self.active_click_params or not self.left_click_mode:
                        print("Hata: Sol tık parametreleri veya modu _click_loop içinde geçersiz. Sol tık durduruluyor.")
                        self.is_left_clicking = False
                        if hasattr(self, 'ui') and self.ui: self.ui.after(0, self._update_global_state_and_ui)
                        if not self.is_right_clicking: break # Exit loop if other is also not running
                        continue # Otherwise, let right click have a chance or sleep

                    params = self.active_click_params['left']
                    mode = self.left_click_mode
                    time_since_last = current_time - self._last_actual_left_click_time
                    current_cps, jitter_x, jitter_y, _ = mode.get_next_action(params, time_since_last)

                    if current_cps <= 0: # Mode signals to stop this click type
                        self.is_left_clicking = False
                        if hasattr(self, 'ui') and self.ui: self.ui.after(0, self._update_global_state_and_ui)
                        if not self.is_right_clicking: break
                        continue
                    
                    current_cps = max(0.1, current_cps) # Prevent division by zero or negative delay
                    if hasattr(self, 'ui') and self.ui: self.ui.after(0, self.ui.update_realtime_cps, current_cps, "Sol")
                    
                    pos = pyautogui.position()
                    pyautogui.click(x=pos.x + int(jitter_x), y=pos.y + int(jitter_y), button='left')
                    
                    self.click_count += 1
                    if hasattr(self, 'ui') and self.ui: self.ui.after(0, self.ui.update_click_count, self.click_count)
                    
                    base_delay = 1.0 / current_cps
                    rand_delay_ms = int(params.get('timing_rand_ms', 0)) # Ensure it's an int, default 0
                    rand_delay_s = random.uniform(-rand_delay_ms / 1000.0, rand_delay_ms / 1000.0)
                    actual_delay = max(0.001, base_delay + rand_delay_s) # Minimum 1ms delay
                    
                    next_left_click_due_time = current_time + actual_delay
                    self._last_actual_left_click_time = current_time
                    executed_click_this_cycle = True
                    if hasattr(mode, 'time_counter'): # For modes like Perlin that use it
                        mode.time_counter += actual_delay

                # Process Right Click (similar logic to left click)
                if self.is_right_clicking and current_time >= next_right_click_due_time:
                    if 'right' not in self.active_click_params or not self.right_click_mode:
                        print("Hata: Sağ tık parametreleri veya modu _click_loop içinde geçersiz. Sağ tık durduruluyor.")
                        self.is_right_clicking = False
                        if hasattr(self, 'ui') and self.ui: self.ui.after(0, self._update_global_state_and_ui)
                        if not self.is_left_clicking: break
                        continue

                    params = self.active_click_params['right']
                    mode = self.right_click_mode
                    time_since_last = current_time - self._last_actual_right_click_time
                    current_cps, jitter_x, jitter_y, _ = mode.get_next_action(params, time_since_last)

                    if current_cps <= 0: # Mode signals to stop
                        self.is_right_clicking = False
                        if hasattr(self, 'ui') and self.ui: self.ui.after(0, self._update_global_state_and_ui)
                        if not self.is_left_clicking: break
                        continue

                    current_cps = max(0.1, current_cps)
                    if hasattr(self, 'ui') and self.ui: self.ui.after(0, self.ui.update_realtime_cps, current_cps, "Sağ")
                    pos = pyautogui.position()
                    pyautogui.click(x=pos.x + int(jitter_x), y=pos.y + int(jitter_y), button='right')
                    self.click_count += 1
                    if hasattr(self, 'ui') and self.ui: self.ui.after(0, self.ui.update_click_count, self.click_count)
                    base_delay = 1.0 / current_cps
                    rand_delay_ms = int(params.get('timing_rand_ms', 0))
                    rand_delay_s = random.uniform(-rand_delay_ms / 1000.0, rand_delay_ms / 1000.0)
                    actual_delay = max(0.001, base_delay + rand_delay_s)
                    next_right_click_due_time = current_time + actual_delay
                    self._last_actual_right_click_time = current_time
                    executed_click_this_cycle = True
                    if hasattr(mode, 'time_counter'):
                        mode.time_counter += actual_delay
                
                # If both click types have been turned off (e.g., by their modes or external toggle)
                if not self.is_left_clicking and not self.is_right_clicking:
                    # self.is_running will be set to False by _update_global_state_and_ui called post-loop
                    break 

                # Sleep management
                if not executed_click_this_cycle:
                    sleep_target = float('inf')
                    if self.is_left_clicking:
                        sleep_target = min(sleep_target, next_left_click_due_time)
                    if self.is_right_clicking:
                        sleep_target = min(sleep_target, next_right_click_due_time)
                    
                    if sleep_target != float('inf'): # Only sleep if there's an active click type with a due time
                        sleep_duration = max(0, sleep_target - time.time())
                        time.sleep(min(max(0.001, sleep_duration), 0.01)) # Max 10ms sleep if no click, min 1ms
                    else:
                        # This case (no click executed, no future click due for active types)
                        # implies both click types might have just been turned off.
                        # Loop should terminate via self.is_running in the next iteration.
                        # A minimal sleep to prevent a potential tight loop.
                        time.sleep(0.001)
                else: # A click was performed
                    time.sleep(0.001) # Short sleep to yield and allow quick check for other type or stop signals

            except Exception as e: # Catch-all for unexpected errors in the loop
                print(f"Click Loop Hatası: {e}")
                if hasattr(self, 'ui') and self.ui: # Check if UI still exists
                    self.ui.after(0, lambda: self.ui.show_error("Döngü Hatası", f"Tıklama döngüsünde hata: {e}"))
                self.is_left_clicking = False
                self.is_right_clicking = False
                # self.is_running will be updated by _update_global_state_and_ui post-loop
                break
        
        # Loop finished (normally, by request, or by error)
        self.is_running = False # Explicitly set global running flag to false
        if hasattr(self, 'ui') and self.ui:
            self.ui.after(0, self._update_global_state_and_ui) # Schedule final UI update
            self.ui.after(0, self._handle_thread_completion) # Schedule thread cleanup tasks
        else: # Handle cases where UI might not exist (e.g. during rapid shutdown or test)
            self._update_global_state_and_ui() # Still update internal state
            self._handle_thread_completion()


    def _handle_thread_completion(self) -> None:
        """Called after the click_thread finishes to clean up."""
        if self.click_thread is not None and not self.click_thread.is_alive():
            self.click_thread = None # Clear the thread object

        # Ensure global running state is false if individual click states are false
        if not (self.is_left_clicking or self.is_right_clicking):
             self.is_running = False

        # Update UI one last time to reflect the truly final state (e.g., IDLE)
        if hasattr(self, 'ui') and self.ui:
            self._update_global_state_and_ui()
        else: # Basic print if UI gone, useful for debugging headless issues
            print(f"Thread completed. Final state: is_running={self.is_running}, left_clicking={self.is_left_clicking}, right_clicking={self.is_right_clicking}")


    def stop_clicking_after_current_cycle(self) -> None:
        """Sets a flag to stop all clicking operations after the current click cycle finishes."""
        self._stop_requested_after_cycle = True

    def set_assign_mode(self, trigger_type: str) -> None:
