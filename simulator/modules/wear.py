from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput

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
    """
    Calculates component degradation based on thermal and mechanical stress.
    """
    def __init__(self, initial_state: WearState):
        self.state = initial_state
        self.input = None
        # PREVENT AttributeError: Initialize output immediately
        self.output = WearOutput(
            cooling_efficiency=1.0 - initial_state.cooling_efficiency_loss,
            torque_loss_factor=initial_state.torque_loss_factor
        )

    def apply_config(self, cfg):
        self.spec = cfg
        self.temp_threshold = cfg.temp_threshold
        self.thermal_stress_factor = cfg.thermal_stress_factor
        self.load_stress_factor = cfg.load_stress_factor
        self.rpm_threshold = cfg.rpm_threshold
        self.rpm_stress_factor = cfg.rpm_stress_factor
        self.cooling_degradation_scale = cfg.cooling_degradation_scale
        self.torque_degradation_scale = cfg.torque_degradation_scale

    def update(self, dt: float):
        if self.input is None: return
        i = self.input
        s = self.state

        # 1. Stress calculation
        thermal_stress = max(0.0, i.engine_temp_c - self.temp_threshold) * self.thermal_stress_factor
        load_stress = i.load * self.load_stress_factor
        rpm_stress = max(0.0, i.engine_rpm - self.rpm_threshold) * self.rpm_stress_factor
        
        wear_acceleration = 1.0 + (s.engine_wear * 2.0)
        total_stress = (thermal_stress + load_stress + rpm_stress) * wear_acceleration
        
        # 2. Accumulation
        s.engine_wear = min(1.0, s.engine_wear + total_stress * dt)

        # 3. Parameter degradation
        s.cooling_efficiency_loss = s.engine_wear * self.cooling_degradation_scale
        s.torque_loss_factor = s.engine_wear * self.torque_degradation_scale

        self.output = WearOutput(
            cooling_efficiency=max(0.1, 1.0 - s.cooling_efficiency_loss),
            torque_loss_factor=s.torque_loss_factor
        )