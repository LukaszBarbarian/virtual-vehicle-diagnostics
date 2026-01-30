# simulator/modules/vehicle.py
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
    """Vehicle dynamics model with integrated braking and friction."""
    def __init__(self, initial_state: VehicleState):
        self.state = initial_state
        self.drivetrain_efficiency = 0.9
        self.rolling_resistance = 0.015
        self.load_scale = 5000.0 

    def apply_config(self, cfg: VehicleSpecification):
        self.spec = cfg
        self.state.mass_kg = cfg.mass_kg
        self.wheel_radius = cfg.wheel_radius_m
        self.tire_grip_coefficient = getattr(cfg, 'tire_grip', 1.0)
        self.max_tire_force = self.state.mass_kg * 9.81 * self.tire_grip_coefficient

    def update(self, dt: float):
        i = self.input
        s = self.state

        total_mass = s.mass_kg + i.cargo_mass_kg
        v_mps = s.speed_kmh / 3.6

        # 1. Driving Force (Traction)
        wheel_torque = i.torque_nm * i.gear_ratio * self.drivetrain_efficiency
        wheel_force_raw = wheel_torque / max(0.01, self.wheel_radius)
        wheel_force = max(-self.max_tire_force, min(self.max_tire_force, wheel_force_raw))

        # 2. Resistance Forces (Drag, Rolling, Incline)
        drag = 0.5 * 1.225 * self.spec.drag_coefficient * self.spec.frontal_area * v_mps**2
        
        # Rolling resistance
        roll_max = self.rolling_resistance * total_mass * 9.81
        if abs(v_mps) < 0.1:
            roll = min(abs(wheel_force), roll_max) * (1 if wheel_force > 0 else -1)
        else:
            roll = roll_max * (1 if v_mps > 0 else -1)

        # Incline (Gravity)
        slope_force = total_mass * 9.81 * (i.road_incline_pct / 100.0)

        # Initialize net_force with driving and environmental forces
        net_force = wheel_force - drag - roll - slope_force

        # 3. Braking Logic (Modulated brake force)
        # Max deceleration around 10 m/s2 at full brake
        brake_force_max = total_mass * 10.0
        applied_brake_force = i.brake * brake_force_max

        if abs(v_mps) > 0.05:
            # Brake always acts against current velocity
            net_force -= applied_brake_force * (1 if v_mps > 0 else -1)
        elif i.brake > 0.05:
            # Static braking: if stopped and brake is pressed, net force should not move the car
            # only if external forces (net_force) are smaller than brake capacity
            if abs(net_force) < applied_brake_force:
                net_force = 0
            else:
                # If slope is so steep that brakes can't hold, the car will slide
                net_force -= applied_brake_force * (1 if net_force > 0 else -1)

        # 4. Motion Integration
        acc = net_force / total_mass
        s.acc_mps2 = acc
        
        new_v_mps = v_mps + acc * dt
        
        # Stability check: prevent the car from reversing due to friction/braking forces
        if (v_mps > 0 and new_v_mps < 0) or (v_mps < 0 and new_v_mps > 0):
            if i.brake > 0.1 or abs(wheel_force) < roll_max:
                new_v_mps = 0
        
        if abs(new_v_mps) < 0.001: 
            new_v_mps = 0
        
        s.speed_kmh = new_v_mps * 3.6
        s.load = max(0.0, wheel_force) / self.load_scale


        self.output = VehicleOutput(
            speed_kmh=round(s.speed_kmh, 2),
            acc_mps2=round(s.acc_mps2, 3),
            load=round(s.load, 2)
        )