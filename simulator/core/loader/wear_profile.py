import yaml
from simulator.core.models.model_specification import WearSpecification


class WearProfileLoader:
    @staticmethod
    def load(path: str) -> WearSpecification:
        with open(path) as f:
            d = yaml.safe_load(f)
        return WearSpecification(**d)
