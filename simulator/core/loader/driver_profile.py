import yaml
from simulator.core.models.model_specification import DriverSpecification

class DriverProfileLoader:
    """
    Utility class for loading driver behavior profiles and settings from YAML files.
    """
    @staticmethod
    def load(path: str) -> DriverSpecification:
        """
        Parses a driver configuration file and returns a structured DriverSpecification object.
        """
        with open(path) as f:
            d = yaml.safe_load(f)
        return DriverSpecification(**d)