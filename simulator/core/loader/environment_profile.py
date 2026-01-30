import yaml
from simulator.core.models.model_specification import EnvironmentSpecification

class EnvironmentLoader:
    """
    Utility class for loading environmental parameters, such as ambient temperature and pressure, from YAML files.
    """
    @staticmethod
    def load(path: str) -> EnvironmentSpecification:
        """
        Reads an environment configuration file and initializes a structured EnvironmentSpecification object.
        """
        with open(path) as f:
            d = yaml.safe_load(f)
        return EnvironmentSpecification(**d)