# vehicle.py
from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
from simulator.core.models.model_specification import VehicleSpecification
import math


@dataclass
class VehicleState(BaseState):
    speed_kmh: float
    acc_mps2: float
    mass_kg: float
    load: float


@dataclass
class VehicleInput(BaseInput):
    torque_nm: float
    gear_ratio: float
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

    def apply_config(self, cfg: VehicleSpecification):
        self.state.mass_kg = cfg.mass_kg

        self.drag_coefficient = 0.15
        self.frontal_area = cfg.frontal_area
        self.rolling_resistance = cfg.rolling_resistance
        self.wheel_radius = cfg.wheel_radius_m

        self.drivetrain_efficiency = cfg.drivetrain_efficiency
        self.brake_force_max = cfg.brake_force_max

        # 🔥 NOWE – KLUCZOWE
        self.max_tire_force = 14000        
        self.load_scale = cfg.load_scale            # np. 8000–12000

    def update(self, dt: float):
        i = self.input
        s = self.state

        total_mass = s.mass_kg + i.cargo_mass_kg
        v_mps = s.speed_kmh / 3.6

        # =============================
        # 1️⃣ SIŁA NAPĘDOWA
        # =============================
        wheel_torque = (
            i.torque_nm
            * (i.gear_ratio if i.gear_ratio else 1.0)
            * self.drivetrain_efficiency
        )

        wheel_force_raw = wheel_torque / max(0.001, self.wheel_radius)

        # 🔥 LIMIT TRAKCJI (BEZ TEGO NIE MA LAMBO)
        wheel_force = max(
            -self.max_tire_force,
            min(self.max_tire_force, wheel_force_raw)
        )

        # =============================
        # 2️⃣ OPORY RUCHU
        # =============================
        drag = 0.5 * 1.225 * self.drag_coefficient * self.frontal_area * v_mps ** 2

        # rolling resistance maleje względnie przy dużych prędkościach
        roll = self.rolling_resistance * total_mass * 9.81 * (0.6 + 0.4 * math.exp(-v_mps / 30))

        slope = total_mass * 9.81 * (i.road_incline_pct / 100.0)
        brake = i.brake * self.brake_force_max

        net_force = wheel_force - drag - roll - slope - brake

        # =============================
        # 3️⃣ RUCH
        # =============================
        acc = net_force / total_mass
        s.acc_mps2 = acc

        s.speed_kmh += acc * dt * 3.6
        s.speed_kmh = max(0.0, s.speed_kmh)

        # =============================
        # 4️⃣ LOAD (DO SILNIKA)
        # =============================
        s.load = min(1.0, abs(wheel_force) / self.load_scale)

        self.output = VehicleOutput(
            speed_kmh=s.speed_kmh,
            acc_mps2=s.acc_mps2,
            load=s.load
        )
