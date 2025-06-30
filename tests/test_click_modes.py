import unittest
from unittest.mock import MagicMock, patch
import random

# Add project root to sys.path to allow importing click_modes
import sys
import os
import math # Import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from click_modes import (
    get_click_mode, SabitMode, DalgalıSinüsMode, PatlamaMode,
    GerçekçiPerlinMode, RandomIntervalClickMode, PatternClickMode,
    ClickMode # Base class for isinstance checks
)

class TestClickModes(unittest.TestCase):

    def setUp(self):
        self.mock_app_core = MagicMock()
        # Mock UI within app_core if modes interact with it directly (e.g. for errors)
        self.mock_app_core.ui = MagicMock()
        # Some modes might call app_core.stop_clicking() or similar
        self.mock_app_core.stop_clicking = MagicMock()
        self.mock_app_core.stop_clicking_after_current_cycle = MagicMock()


        # Common params, specific modes might need more
        self.base_params = {
            'peak_cps': 10.0,
            'jitter_px': 5,
            'timing_rand_ms': 10
        }
        random.seed(42) # for reproducible tests if random numbers are involved deeply

    def test_get_click_mode_factory(self):
        modes_to_test = {
            "Sabit": SabitMode,
            "Dalgalı (Sinüs)": DalgalıSinüsMode,
            "Patlama": PatlamaMode,
            "Gerçekçi (Perlin)": GerçekçiPerlinMode,
            "Rastgele Aralık": RandomIntervalClickMode,
            "Pattern (Desen)": PatternClickMode,
        }
        for name, expected_class in modes_to_test.items():
            mode_instance = get_click_mode(name, self.mock_app_core)
            self.assertIsInstance(mode_instance, expected_class)
            self.assertIsInstance(mode_instance, ClickMode) # Check base class

        with self.assertRaises(ValueError):
            get_click_mode("OlmayanMod", self.mock_app_core)

    def test_sabit_mode(self):
        mode = SabitMode(self.mock_app_core)
        params = {**self.base_params}
        cps, jitter_x, jitter_y, _ = mode.get_next_action(params, elapsed_time=1.0)
        self.assertEqual(cps, params['peak_cps'])
        self.assertTrue(-params['jitter_px'] <= jitter_x <= params['jitter_px'])
        self.assertTrue(-params['jitter_px'] <= jitter_y <= params['jitter_px'])

    def test_dalgalı_sinus_mode(self):
        mode = DalgalıSinüsMode(self.mock_app_core)
        params = {**self.base_params, 'peak_cps': 10} # peak_cps is average here
        # Check a few points in time
        cps1, _, _, _ = mode.get_next_action(params, elapsed_time=0.0) # sin(0) = 0 -> peak_cps
        self.assertAlmostEqual(cps1, 10.0)

        cps2, _, _, _ = mode.get_next_action(params, elapsed_time=math.pi/(2*1.5)) # sin(pi/2)=1 -> peak_cps + peak_cps*0.25
        self.assertAlmostEqual(cps2, 10.0 + 10.0 * 0.25)

        cps3, _, _, _ = mode.get_next_action(params, elapsed_time=math.pi/(1.5)) # sin(pi)=0 -> peak_cps
        self.assertAlmostEqual(cps3, 10.0)

    @patch('click_modes.PerlinNoise') # Mock PerlinNoise for predictability
    def test_gercekci_perlin_mode(self, mock_perlin_noise_class):
        # Configure mock instances for noise_cps, noise_x, noise_y
        mock_noise_instance_cps = MagicMock(return_value=0.1) # Example fixed noise value
        mock_noise_instance_x = MagicMock(return_value=0.5)
        mock_noise_instance_y = MagicMock(return_value=-0.3)

        # Have the mock PerlinNoise class return these instances in order
        mock_perlin_noise_class.side_effect = [
            mock_noise_instance_x, # for self.noise_x
            mock_noise_instance_y, # for self.noise_y
            mock_noise_instance_cps  # for self.noise_cps
        ]

        mode = GerçekçiPerlinMode(self.mock_app_core)
        params = {**self.base_params, 'peak_cps': 10, 'jitter_px': 5}

        # Ensure noise generators are assigned
        self.assertIsNotNone(mode.noise_x)
        self.assertIsNotNone(mode.noise_y)
        self.assertIsNotNone(mode.noise_cps)

        cps, jitter_x, jitter_y, _ = mode.get_next_action(params, elapsed_time=1.0)

        expected_cps_fluctuation = 0.1 * (params['peak_cps'] * 0.4)
        expected_cps = params['peak_cps'] + expected_cps_fluctuation
        self.assertAlmostEqual(cps, expected_cps)

        expected_jitter_x = 0.5 * params['jitter_px']
        expected_jitter_y = -0.3 * params['jitter_px']
        self.assertAlmostEqual(jitter_x, expected_jitter_x)
        self.assertAlmostEqual(jitter_y, expected_jitter_y)

    def test_patlama_mode(self):
        mode = PatlamaMode(self.mock_app_core)
        params = {**self.base_params, 'peak_cps': 20, 'burst_duration': 1.0}
        # duration = 1s, ramp_time = 0.3s, peak_time = 0.4s

        # Ramp up phase
        cps_ramp_start, _, _, _ = mode.get_next_action(params, elapsed_time=0.0)
        self.assertAlmostEqual(cps_ramp_start, 0.0)
        cps_ramp_mid, _, _, _ = mode.get_next_action(params, elapsed_time=0.15) # Halfway ramp up
        self.assertAlmostEqual(cps_ramp_mid, params['peak_cps'] * 0.5)

        # Peak phase
        cps_peak, _, _, _ = mode.get_next_action(params, elapsed_time=0.35) # During peak
        self.assertAlmostEqual(cps_peak, params['peak_cps'])

        # Ramp down phase
        cps_ramp_down_mid, _, _, _ = mode.get_next_action(params, elapsed_time=0.85) # Halfway ramp down (0.7 + 0.15)
        self.assertAlmostEqual(cps_ramp_down_mid, params['peak_cps'] * 0.5)

        # After duration
        cps_after, _, _, _ = mode.get_next_action(params, elapsed_time=1.1)
        self.assertEqual(cps_after, 0) # Should signal stop
        self.mock_app_core.stop_clicking_after_current_cycle.assert_called_once()

    def test_random_interval_mode(self):
        mode = RandomIntervalClickMode(self.mock_app_core)
        min_c, max_c = 5.0, 15.0
        params = {**self.base_params, 'min_cps_random': min_c, 'max_cps_random': max_c}

        for _ in range(10): # Test a few times due to randomness
            cps, _, _, _ = mode.get_next_action(params, elapsed_time=1.0)
            self.assertTrue(min_c <= cps <= max_c)

        # Test edge case where min_cps > max_cps (should use peak_cps as fallback)
        params_invalid = {**self.base_params, 'peak_cps': 10, 'min_cps_random': 15.0, 'max_cps_random': 5.0}
        cps_fallback, _, _, _ = mode.get_next_action(params_invalid, elapsed_time=1.0)
        self.assertEqual(cps_fallback, params_invalid['peak_cps'])

    def test_pattern_mode(self):
        mode = PatternClickMode(self.mock_app_core)
        pattern_str = "100-200-50" # delays in ms
        expected_delays_s = [0.1, 0.2, 0.05]
        params = {**self.base_params, 'click_pattern': pattern_str}

        # First call parses the pattern
        cps1, _, _, _ = mode.get_next_action(params, elapsed_time=0.1)
        self.assertAlmostEqual(cps1, 1.0 / expected_delays_s[0])
        self.assertEqual(mode.current_pattern_index, 1)

        cps2, _, _, _ = mode.get_next_action(params, elapsed_time=0.2)
        self.assertAlmostEqual(cps2, 1.0 / expected_delays_s[1])
        self.assertEqual(mode.current_pattern_index, 2)

        cps3, _, _, _ = mode.get_next_action(params, elapsed_time=0.3)
        self.assertAlmostEqual(cps3, 1.0 / expected_delays_s[2])
        self.assertEqual(mode.current_pattern_index, 0) # Wraps around

    def test_pattern_mode_invalid_pattern(self):
        mode = PatternClickMode(self.mock_app_core)
        params_invalid_pattern = {**self.base_params, 'click_pattern': "abc-def"}

        # First call, parsing fails
        cps, _, _, _ = mode.get_next_action(params_invalid_pattern, elapsed_time=0.1)
        self.mock_app_core.ui.show_error.assert_called_once()
        # It should now return 0 CPS as parsing fails and signals stop
        self.assertAlmostEqual(cps, 0)
        # And core.stop_clicking should have been called by the mode's _parse_pattern
        self.mock_app_core.stop_clicking.assert_called_once()

    def test_pattern_mode_empty_pattern(self):
        mode = PatternClickMode(self.mock_app_core)
        params_empty_pattern = {**self.base_params, 'click_pattern': " - "} # only separators

        cps, _, _, _ = mode.get_next_action(params_empty_pattern, elapsed_time=0.1)
        self.mock_app_core.ui.show_error.assert_called_once()
        self.assertAlmostEqual(cps, 0) # Signals stop
        self.mock_app_core.stop_clicking.assert_called_once()


    def test_reset_modes(self):
        # Test reset for a mode that has internal state, e.g., PatternClickMode or GerçekçiPerlinMode

        # Pattern Mode Reset
        pattern_mode = PatternClickMode(self.mock_app_core)
        params_pattern = {**self.base_params, 'click_pattern': "100-200"}
        pattern_mode.get_next_action(params_pattern, 0.1) # Move index
        self.assertEqual(pattern_mode.current_pattern_index, 1)
        pattern_mode.reset()
        self.assertEqual(pattern_mode.current_pattern_index, 0)
        # Reset should also clear parsed pattern to be re-parsed on next get_next_action with potentially new params
        self.assertEqual(pattern_mode.pattern_delays, [])


        # GerçekçiPerlinMode reset (check if noise objects are re-created/re-seeded)
        with patch('click_modes.PerlinNoise') as mock_perlin_class_for_reset:
            # Configure the mock class to return a new mock instance each time it's called
            # This simulates creating new PerlinNoise objects. Name them for clarity in debug.
            mock_instances_list = [
                MagicMock(name="NoiseX_Init"), MagicMock(name="NoiseY_Init"), MagicMock(name="NoiseCPS_Init"),
                MagicMock(name="NoiseX_Reset"), MagicMock(name="NoiseY_Reset"), MagicMock(name="NoiseCPS_Reset")
            ]
            mock_perlin_class_for_reset.side_effect = iter(mock_instances_list)

            perlin_mode = GerçekçiPerlinMode(self.mock_app_core)
            # After __init__, the first 3 mocks from side_effect should have been used.
            self.assertEqual(mock_perlin_class_for_reset.call_count, 3)

            noise_x_obj_before_reset = perlin_mode.noise_x # This is MagicMock(name="NoiseX_Init")

            # Get the mock that will be assigned to noise_x during reset
            # This relies on the order in the original list: NoiseX_Reset is at index 3
            expected_noise_x_after_reset = mock_instances_list[3]

            perlin_mode.reset() # This will call PerlinNoise() 3 more times

            self.assertEqual(mock_perlin_class_for_reset.call_count, 6) # 3 in init + 3 in reset

            self.assertNotEqual(id(noise_x_obj_before_reset), id(perlin_mode.noise_x))
            # Check if it's the specific mock instance we expect from the side_effect list
            self.assertIs(perlin_mode.noise_x, expected_noise_x_after_reset)
            # Check the internal _mock_name (an internal detail, but useful for named MagicMocks)
            self.assertEqual(perlin_mode.noise_x._mock_name, "NoiseX_Reset")


if __name__ == '__main__':
    # Need to adjust path if running tests directly for imports to work
    # This is handled by sys.path.insert at the top for when tests are run via `python -m unittest discover`
    import math # Make math available for DalgalıSinüsMode test
    unittest.main()
