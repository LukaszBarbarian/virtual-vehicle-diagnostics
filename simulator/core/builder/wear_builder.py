from simulator.core.models.model_specification import WearSpecification
from simulator.modules.wear import WearModule, WearState

class WearBuilder:
    """
    Factory class responsible for initializing the component wear tracking module.
    """
    @staticmethod
    def build(spec: WearSpecification) -> WearModule:
        """
        Creates a WearModule with zeroed initial states and applies the wear rate configuration.
        """
        wear = WearModule(WearState(0.0, 0.0, 0.0, 0.0))
        wear.apply_config(spec)
        return wear