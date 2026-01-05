import yaml
from simulator.core.models.model_specification import *

class CarProfileLoader:
    @staticmethod
    def load(path: str) -> CarSpecification:
        with open(path) as f:
            data = yaml.safe_load(f)

        return CarSpecification(
            name=data["name"],
            engine=EngineSpecification(**data["engine"]),
            gearbox=GearboxSpecification(**data["gearbox"]),
            vehicle=VehicleSpecification(**data["vehicle"]),
            thermal=ThermalSpecification(**data["thermals"])
        )
