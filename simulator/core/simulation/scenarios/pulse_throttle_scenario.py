from simulator.core.simulation.scenarios.driver_scenario import DrivingScenario


class PulsingThrottleScenario(DrivingScenario):
    name = "pulsing_throttle"

    def get_driver_command(self, t, state):
        if int(t) % 10 < 5:
            pedal = 0.4
        else:
            pedal = 0.2

        return {
            "pedal": pedal,
            "brake": 0.0,
            "cargo_mass_kg": 0.0
        }
