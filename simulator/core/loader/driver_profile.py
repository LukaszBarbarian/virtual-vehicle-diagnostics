import yaml
from simulator.core.models.model_specification import DriverSpecification


class DriverProfileLoader:
    @staticmethod
    def load(path: str) -> DriverSpecification:
        with open(path) as f:
            d = yaml.safe_load(f)
        return DriverSpecification(**d)
