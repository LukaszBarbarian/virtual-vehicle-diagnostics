import yaml
from core.config_models import *

class CarProfileLoader:
    @staticmethod
    def load(path: str) -> CarConfig:
        with open(path) as f:
            data = yaml.safe_load(f)

        return CarConfig(
            name=data["name"],
            engine=EngineConfig(**data["engine"]),
            gearbox=GearboxConfig(**data["gearbox"]),
            vehicle=VehicleConfig(**data["vehicle"]),
            thermal=ThermalConfig(**data["thermals"]),
            driver=DriverConfig(**data["driver"])
        )
