from simulator.core.models.model_specification import WearSpecification
from simulator.modules.wear import WearModule, WearState


class WearBuilder:
    @staticmethod
    def build(spec: WearSpecification) -> WearModule:
        wear = WearModule(WearState(0.0, 0.0, 0.0, 0.0))
        wear.apply_config(spec)
        return wear
