from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
from simulator.core.models.model_specification import DriverSpecification


@dataclass
class DriverState(BaseState):
    pedal: float = 0.0          # pozycja stopy
    throttle: float = 0.0       # wyjście po mapie
    brake: float = 0.0
    cargo_mass_kg: float = 0.0
    driver_style: str = "normal"
    throttle_rate: float = 0.0


@dataclass
class DriverInput(BaseInput):
    engine_rpm: float
    max_rpm: float


@dataclass
class DriverOutput(BaseOutput):
    throttle: float
    throttle_rate: float
    brake: float
    cargo_mass_kg: float


class DriverModule(BaseModule):
    def __init__(self, initial_state: DriverState):
        self.state = initial_state
        self.output = None
        self.input = None
        self.t = 0.0
        self.external_pedal_target = None
        self.external_brake_target = 0.0


    def set_external_brake(self, value: float):
        """Sets the external braking intent."""
        self.external_brake_target = value

    def set_external_pedal(self, pedal: float | None):
        """
        Ustawia zewnętrzną intencję kierowcy (np. z UI / Kafki)
        pedal = None → wróć do profilu
        """
        if pedal is None:
            self.external_pedal_target = None
        else:
            self.external_pedal_target = max(0.0, min(1.0, pedal))


    def apply_config(self, cfg: DriverSpecification):
        self.ramp_time = cfg.ramp_time
        self.cruise_pedal = cfg.cruise_throttle
        self.cruise_time = cfg.cruise_time
        self.decel_time = cfg.decel_time
        self.final_pedal = cfg.final_throttle
        self.state.driver_style = cfg.driver_style

    def update(self, dt: float):
        self.t += dt

        # =========================
        # FAZY JAZDY
        # =========================

        if self.external_pedal_target is not None:
            target_pedal = self.external_pedal_target

        elif self.t < self.ramp_time:
            target_pedal = self.cruise_pedal * (self.t / self.ramp_time)
        elif self.t < self.ramp_time + self.cruise_time:
            target_pedal = self.cruise_pedal
        elif self.t < self.ramp_time + self.cruise_time + self.decel_time:
            ratio = (self.t - self.ramp_time - self.cruise_time) / self.decel_time
            target_pedal = (
                self.cruise_pedal * (1.0 - ratio)
                + self.final_pedal * ratio
            )
        else:
            target_pedal = self.final_pedal

        # =========================
        # REAKCJA NA RPM (ludzka)
        # =========================
        rpm_ratio = self.input.engine_rpm / max(1.0, self.input.max_rpm)
        if rpm_ratio > 0.92:
            target_pedal *= 0.85
        elif rpm_ratio > 0.85:
            target_pedal *= 0.95

        target_pedal = max(0.0, min(1.0, target_pedal))

        # =========================
        # FILTR STOPY (bezwładność nogi)
        # =========================
        response = 3.0 if self.state.driver_style == "sport" else 1.5
        self.state.pedal += (target_pedal - self.state.pedal) * response * dt
        self.state.pedal = max(0.0, min(1.0, self.state.pedal))

        # =========================
        # MAPA PEDAŁU
        # =========================
        prev_throttle = self.state.throttle

        self.state.throttle = self.throttle_map(
            self.state.pedal,
            self.state.driver_style
        )

        # =========================
        # TEMPO ZMIANY GAZU (KLUCZ!)
        # =========================
        self.state.throttle_rate = (
            self.state.throttle - prev_throttle
        ) / max(dt, 1e-4)

        brake_response = 4.0 if self.state.driver_style == "sport" else 2.5
        self.state.brake += (self.external_brake_target - self.state.brake) * brake_response * dt
        self.state.brake = max(0.0, min(1.0, self.state.brake))

        self.output = DriverOutput(
            throttle=self.state.throttle,
            throttle_rate=self.state.throttle_rate,
            brake=self.state.brake, # Now passing the filtered value
            cargo_mass_kg=self.state.cargo_mass_kg
        )



    # =========================
    # MAPA PEDAŁU
    # =========================
    def throttle_map(self, pedal: float, mode: str = "normal") -> float:
        pedal = max(0.0, min(1.0, pedal))

        if mode == "eco":
            return pedal ** 1.8

        if mode == "sport":
            return pedal ** 0.7

        # NORMAL
        if pedal < 0.15:
            return pedal * 0.4
        elif pedal < 0.5:
            return 0.06 + (pedal - 0.15) * 0.9
        else:
            return 0.375 + (pedal - 0.5) * 1.25
