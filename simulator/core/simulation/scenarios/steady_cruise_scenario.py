from simulator.core.simulation.scenarios.driver_scenario import DrivingScenario


class SteadyCruiseScenario(DrivingScenario):
    name = "steady_cruise_0_20"

    def get_driver_command(self, t, state):
        return {
            "pedal": 0.20,
            "brake": 0.0,
            "cargo_mass_kg": 0.0
        }
