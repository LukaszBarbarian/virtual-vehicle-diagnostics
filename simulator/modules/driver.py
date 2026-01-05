from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
from simulator.core.models.model_specification import DriverSpecification

@dataclass
class DriverState(BaseState):
    throttle: float = 0.2
    brake: float = 0.0
    cargo_mass_kg: float = 0.0
    driver_style: str = "normal"

@dataclass
class DriverInput(BaseInput):
    engine_rpm: float
    max_rpm: float

@dataclass
class DriverOutput(BaseOutput):
    throttle: float
    brake: float
    cargo_mass_kg: float


class DriverModule(BaseModule):
    def __init__(self, initial_state: DriverState):
        self.state = initial_state
        self.output = None
        self.t = 0.0
        self.input = None
        self.cruise_throttle = 0.0


    def apply_config(self, cfg: DriverSpecification):
        self.ramp_time = cfg.ramp_time
        self.cruise_throttle = cfg.cruise_throttle
        self.cruise_time = cfg.cruise_time
        self.decel_time = cfg.decel_time
        self.final_throttle = cfg.final_throttle
        self.state.driver_style = cfg.driver_style

    def update(self, dt: float):
        self.t += dt

        target = self.cruise_throttle

        # reakcja na obroty silnika
        rpm_ratio = self.input.engine_rpm / self.input.max_rpm

        if rpm_ratio > 0.92:
            target *= 0.7
        elif rpm_ratio > 0.85:
            target *= 0.85

        # łagodne sterowanie
        self.state.throttle += (target - self.state.throttle) * 2.0 * dt

        self.output = DriverOutput(
            throttle=self.state.throttle,
            brake=0.0,
            cargo_mass_kg=self.state.cargo_mass_kg
        )