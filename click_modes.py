import time
import random
import math
from perlin_noise import PerlinNoise

class ClickMode:
    """Base class for all click modes."""
    def __init__(self, app_core):
        self.app_core = app_core
        # Perlin noise can be initialized by modes that need it
        self.noise_x = None
        self.noise_y = None
        self.noise_cps = None
        self.time_counter = 0.0

    def get_next_action(self, params: dict, elapsed_time: float) -> tuple[float, int, int, float]:
        """
        Calculates the next click action based on the mode.

        Args:
            params (dict): Dictionary of parameters for the click mode.
            elapsed_time (float): Time elapsed since clicking started.

        Returns:
            tuple[float, int, int, float]: current_cps, jitter_x, jitter_y, delay_multiplier
            delay_multiplier is used by some modes to adjust the base delay dynamically.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def reset(self):
        """Resets any internal state of the click mode."""
        self.time_counter = 0.0
        # Re-seed noises for variety if desired, or keep them for consistency
        # Only initialize if they were used
        if self.noise_x:
            self.noise_x = PerlinNoise(octaves=4, seed=random.randint(1, 1000))
        if self.noise_y:
            self.noise_y = PerlinNoise(octaves=4, seed=random.randint(1, 1000))
        if self.noise_cps:
            self.noise_cps = PerlinNoise(octaves=2, seed=random.randint(1, 1000))


class SabitMode(ClickMode):
    def get_next_action(self, params: dict, elapsed_time: float) -> tuple[float, int, int, float]:
        peak_cps = params['peak_cps']
        jitter_intensity = params['jitter_px']
        current_cps = peak_cps
        jitter_x = random.randint(-jitter_intensity, jitter_intensity)
        jitter_y = random.randint(-jitter_intensity, jitter_intensity)
        return current_cps, jitter_x, jitter_y, 1.0

class DalgalıSinüsMode(ClickMode):
    def get_next_action(self, params: dict, elapsed_time: float) -> tuple[float, int, int, float]:
        peak_cps = params['peak_cps']
        jitter_intensity = params['jitter_px']
        fluctuation = math.sin(elapsed_time * 1.5) * (peak_cps * 0.25)
        current_cps = peak_cps + fluctuation
        jitter_x = random.randint(-jitter_intensity, jitter_intensity)
        jitter_y = random.randint(-jitter_intensity, jitter_intensity)
        return current_cps, jitter_x, jitter_y, 1.0

class PatlamaMode(ClickMode):
    def get_next_action(self, params: dict, elapsed_time: float) -> tuple[float, int, int, float]:
        peak_cps = params['peak_cps']
        jitter_intensity = params['jitter_px']
        duration = params.get('burst_duration', 5.0) # Default to 5s if not provided

        # Ensure ramp_time is not zero to avoid division by zero
        ramp_time_factor = 0.3
        ramp_time = duration * ramp_time_factor
        if ramp_time == 0: # Handle cases where duration might be very small
            ramp_time = 0.1

        peak_time = duration - (2 * ramp_time)
        if peak_time < 0: # Adjust if duration is too short for distinct phases
            peak_time = 0
            ramp_time = duration / 2


        current_cps = 0
        if elapsed_time < ramp_time:
            current_cps = (elapsed_time / ramp_time) * peak_cps
        elif elapsed_time < ramp_time + peak_time:
            current_cps = peak_cps
        elif elapsed_time < duration:
            current_cps = (1 - (elapsed_time - ramp_time - peak_time) / ramp_time) * peak_cps
        else:
            # Signal to stop clicking after burst is complete
            # This can be done by returning a CPS of 0 or a special flag
            # For now, let's have the core app handle stopping via this signal
            self.app_core.stop_clicking_after_current_cycle() # Request stop
            return 0,0,0, 1.0 # Return 0 CPS to effectively stop

        jitter_x = random.randint(-jitter_intensity, jitter_intensity)
        jitter_y = random.randint(-jitter_intensity, jitter_intensity)
        return current_cps, jitter_x, jitter_y, 1.0

class GerçekçiPerlinMode(ClickMode):
    def __init__(self, app_core):
        super().__init__(app_core)
        # Initialize Perlin noise generators for this mode
        self.noise_x = PerlinNoise(octaves=4, seed=random.randint(1, 1000))
        self.noise_y = PerlinNoise(octaves=4, seed=random.randint(1, 1000))
        self.noise_cps = PerlinNoise(octaves=2, seed=random.randint(1, 1000))

    def get_next_action(self, params: dict, elapsed_time: float) -> tuple[float, int, int, float]:
        peak_cps = params['peak_cps']
        jitter_intensity = params['jitter_px']

        cps_noise = self.noise_cps(self.time_counter)
        cps_fluctuation = cps_noise * (peak_cps * 0.4)
        current_cps = peak_cps + cps_fluctuation

        jitter_x = self.noise_x(self.time_counter) * jitter_intensity
        jitter_y = self.noise_y(self.time_counter) * jitter_intensity

        # Increment time_counter based on the effective delay of the last cycle
        # This will be passed back from the core loop or estimated here
        # The core loop will update self.time_counter using the actual_delay
        return current_cps, jitter_x, jitter_y, 1.0

class RandomIntervalClickMode(ClickMode):
    def __init__(self, app_core):
        super().__init__(app_core)
        # Additional parameters for this mode will be fetched from UI
        # e.g., min_cps, max_cps

    def get_next_action(self, params: dict, elapsed_time: float) -> tuple[float, int, int, float]:
        min_cps = params.get('min_cps_random', 5.0) # Default min CPS
        max_cps = params.get('max_cps_random', params['peak_cps']) # Default max CPS, can be linked to main CPS slider
        jitter_intensity = params['jitter_px']

        if min_cps <= 0 or max_cps <=0 or min_cps > max_cps:
            # Fallback or error, though UI validation should prevent this
            current_cps = params['peak_cps']
        else:
            current_cps = random.uniform(min_cps, max_cps)

        jitter_x = random.randint(-jitter_intensity, jitter_intensity)
        jitter_y = random.randint(-jitter_intensity, jitter_intensity)

        return current_cps, jitter_x, jitter_y, 1.0

class PatternClickMode(ClickMode):
    def __init__(self, app_core):
        super().__init__(app_core)
        self.pattern_delays = []
        self.current_pattern_index = 0

    def _parse_pattern(self, pattern_str: str):
        try:
            parsed_delays = [float(delay) / 1000.0 for delay in pattern_str.split('-') if delay.strip()]
            if not parsed_delays:
                # This case handles patterns like " - " or "" or "abc" if float conversion fails early for all parts
                self.app_core.ui.show_error("Pattern Hatası", "Pattern boş veya geçersiz karakterler içeriyor.\nÖrnek: 100-50-200")
                self.pattern_delays = [] # Ensure it's empty
                self.app_core.stop_clicking() # Signal core to stop
                return False # Indicate parsing failed
            self.pattern_delays = parsed_delays
            return True # Indicate parsing succeeded
        except ValueError: # Catches float conversion errors for parts like "abc" in "100-abc-50"
            self.app_core.ui.show_error("Pattern Hatası", "Pattern sayısal olmayan değerler içeriyor veya format hatalı.\nÖrnek: 100-50-200")
            self.pattern_delays = [] # Ensure it's empty
            self.app_core.stop_clicking() # Signal core to stop
            return False # Indicate parsing failed


    def reset(self):
        super().reset()
        self.current_pattern_index = 0
        self.pattern_delays = [] # Clear parsed pattern on reset

    def get_next_action(self, params: dict, elapsed_time: float) -> tuple[float, int, int, float]:
        if not self.pattern_delays:
            pattern_string = params.get('click_pattern', "100")
            if not self._parse_pattern(pattern_string) or not self.pattern_delays:
                 # Parsing failed and set pattern_delays to [], or it was already empty.
                 # stop_clicking was already called by _parse_pattern if it failed there.
                 return 0,0,0,1.0 # Signal stop to click loop immediately

        # If self.pattern_delays is still empty here, it means parsing failed or yielded no valid delays.
        if not self.pattern_delays:
            return 0,0,0,1.0 # Should have been caught above, but as a safeguard.

        delay_for_this_step = self.pattern_delays[self.current_pattern_index]

        if delay_for_this_step <= 0: # Avoid division by zero if pattern has invalid delay
            current_cps = 1000 # Effectively, a very short delay
        else:
            current_cps = 1.0 / delay_for_this_step

        jitter_intensity = params['jitter_px']
        jitter_x = random.randint(-jitter_intensity, jitter_intensity)
        jitter_y = random.randint(-jitter_intensity, jitter_intensity)

        self.current_pattern_index = (self.current_pattern_index + 1) % len(self.pattern_delays)

        # This mode directly controls delay, so CPS is derived.
        # The core loop's delay calculation will use this CPS.
        return current_cps, jitter_x, jitter_y, 1.0


# Factory to get click mode instances
def get_click_mode(mode_name: str, app_core) -> ClickMode:
    modes = {
        "Sabit": SabitMode,
        "Dalgalı (Sinüs)": DalgalıSinüsMode,
        "Patlama": PatlamaMode,
        "Gerçekçi (Perlin)": GerçekçiPerlinMode,
        "Rastgele Aralık": RandomIntervalClickMode,
        "Pattern (Desen)": PatternClickMode,
    }
    mode_class = modes.get(mode_name)
    if not mode_class:
        raise ValueError(f"Unknown click mode: {mode_name}")
    return mode_class(app_core)
