from dataclasses import dataclass
from core.base import BaseModule, BaseState, BaseInput, BaseOutput

@dataclass
class WearState(BaseState):
    engine_wear: float
    gearbox_wear: float
    cooling_efficiency_loss: float
    torque_loss_factor: float

@dataclass
class WearInput(BaseInput):
    engine_temp_c: float
    oil_temp_c: float
    load: float
    engine_rpm: float
    gearbox_temp_c: float

@dataclass
class WearOutput(BaseOutput):
    cooling_efficiency: float
    torque_loss_factor: float

class WearModule(BaseModule):
    def __init__(self, initial_state: WearState):
        self.state = initial_state
        self.input = None
        self.output = None

    def apply_config(self, config):
        return super().apply_config(config)

    def update(self, dt: float):
        i = self.input
        s = self.state

        # zmniejszone współczynniki, żeby wear rosło wolniej
        thermal_stress = max(0.0, i.engine_temp_c - 95.0) * 0.0002
        load_stress = i.load * 0.0001
        rpm_stress = max(0.0, i.engine_rpm - 4500.0) * 0.000001

        s.engine_wear += (thermal_stress + load_stress + rpm_stress) * dt
        s.engine_wear = min(1.0, s.engine_wear)

        # degradacja chłodzenia i momentu
        s.cooling_efficiency_loss = s.engine_wear * 0.4
        s.torque_loss_factor = s.engine_wear * 0.35

        self.output = WearOutput(
            cooling_efficiency=1.0 - s.cooling_efficiency_loss,
            torque_loss_factor=s.torque_loss_factor
        )
