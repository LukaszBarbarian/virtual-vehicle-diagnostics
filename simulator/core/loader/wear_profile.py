import yaml
from simulator.core.models.model_specification import WearSpecification

class WearProfileLoader:
    """
    Utility class for loading component wear parameters and degradation coefficients from YAML files.
    """
    @staticmethod
    def load(path: str) -> WearSpecification:
        """
        Parses a wear configuration file and maps it to a structured WearSpecification object.
        """
        with open(path) as f:
            d = yaml.safe_load(f)
        return WearSpecification(**d)