class DrivingScenario:
    name: str

    def reset(self):
        pass

    def get_driver_command(self, t: float, state) -> dict:
        """
        Returns:
        {
            "pedal": float,
            "brake": float,
            "cargo_mass_kg": float
        }
        """
