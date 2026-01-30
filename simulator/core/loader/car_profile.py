import yaml
from simulator.core.models.model_specification import *

class CarProfileLoader:
    """
    Utility class for loading car technical specifications from external YAML configuration files.
    """
    @staticmethod
    def load(path: str) -> CarSpecification:
        """
        Parses a YAML file and maps its contents to a structured CarSpecification object.
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        return CarSpecification(
            name=data["name"],
            engine=EngineSpecification(**data["engine"]),
            gearbox=GearboxSpecification(**data["gearbox"]),
            vehicle=VehicleSpecification(**data["vehicle"]),
            thermal=ThermalSpecification(**data["thermals"])
        )