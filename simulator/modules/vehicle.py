# vehicle.py
from dataclasses import dataclass
from core.base import BaseModule, BaseState, BaseInput, BaseOutput
from core.config_models import VehicleConfig

@dataclass
class VehicleState(BaseState):
    speed_kmh: float
    acc_mps2: float
    mass_kg: float
    load: float

@dataclass
class VehicleInput(BaseInput):
    torque_nm: float
    gear_ratio: float  # oczekujemy totalnego przełożenia (gear*final_drive)
    brake: float
    cargo_mass_kg: float
    road_incline_pct: float

@dataclass
class VehicleOutput(BaseOutput):
    speed_kmh: float
    acc_mps2: float
    load: float

class VehicleModule(BaseModule):
    def __init__(self, initial_state: VehicleState):
        self.state = initial_state
        self.input = None
        self.output = None



    def apply_config(self, cfg: VehicleConfig):
        self.state.mass_kg = cfg.mass_kg
        self.drag_coefficient = cfg.drag_coefficient
        self.rolling_resistance = cfg.rolling_resistance
        self.frontal_area = cfg.frontal_area
        self.wheel_radius = cfg.wheel_radius_m

        self.drivetrain_efficiency = cfg.drivetrain_efficiency
        self.brake_force_max = cfg.brake_force_max
        self.load_scale = cfg.load_scale


    def update(self, dt: float):
        i = self.input
        s = self.state

        total_mass = s.mass_kg + i.cargo_mass_kg

        # wheel force = torque_at_wheel / wheel_radius
        # torque at wheel = engine_torque * total_gear_ratio * drivetrain_efficiency
        drivetrain_efficiency = self.drivetrain_efficiency
        wheel_torque = i.torque_nm * (i.gear_ratio if i.gear_ratio is not None else 1.0) * drivetrain_efficiency
        wheel_force = wheel_torque / max(0.001, self.wheel_radius)

        # aerodynamic drag
        v_mps = s.speed_kmh / 3.6
        drag = 0.5 * 1.225 * self.drag_coefficient * self.frontal_area * v_mps ** 2
        roll = self.rolling_resistance * total_mass * 9.81
        slope = total_mass * 9.81 * (i.road_incline_pct / 100.0)

        brake_force = i.brake * self.brake_force_max


        net_force = wheel_force - drag - roll - slope - brake_force

        acc = net_force / total_mass

        s.acc_mps2 = acc
        s.speed_kmh += acc * dt * 3.6
        s.speed_kmh = max(0.0, s.speed_kmh)

        s.load = min(1.0, abs(wheel_force) / self.load_scale)


        self.output = VehicleOutput(
            speed_kmh=s.speed_kmh,
            acc_mps2=s.acc_mps2,
            load=s.load
        )
