import yaml
from simulator.core.models.model_specification import EnvironmentSpecification


class EnvironmentLoader:
    @staticmethod
    def load(path: str) -> EnvironmentSpecification:
        with open(path) as f:
            d = yaml.safe_load(f)
        return EnvironmentSpecification(**d)
