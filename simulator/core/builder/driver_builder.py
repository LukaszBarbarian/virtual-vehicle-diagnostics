# simulator/core/builder/driver_builder.py

from simulator.core.models.model_specification import DriverSpecification
from simulator.modules.driver import DriverModule, DriverState

class DriverBuilder:
    """
    Factory class responsible for creating and configuring the driver module instance.
    """
    @staticmethod
    def build(spec: DriverSpecification) -> DriverModule:
        """
        Constructs a DriverModule with initial states and applies configuration from the provided specification.
        """
        driver = DriverModule(
            DriverState(
                throttle=0.0,
                brake=0.0,
                cargo_mass_kg=0.0,
                driver_style=spec.driver_style
            )
        )
        driver.apply_config(spec)
        return driver