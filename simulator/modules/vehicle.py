# simulator/modules/vehicle.py
from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
from simulator.core.models.model_specification import VehicleSpecification
import math

@dataclass
class VehicleState(BaseState):
    """
    Tracks the physical movement of the vehicle including speed, acceleration, and total mass.
    """
    speed_kmh: float
    acc_mps2: float
    mass_kg: float
    load: float

@dataclass
class VehicleInput(BaseInput):
    """
    External forces and parameters affecting vehicle motion, such as torque, braking, and road geometry.
    """
    torque_nm: float
    gear_ratio: float
    brake: float
    cargo_mass_kg: float
    road_incline_pct: float

@dataclass
class VehicleOutput(BaseOutput):
    """
    Resulting kinematic data exported to other simulation modules.
    """
    speed_kmh: float
    acc_mps2: float
    load: float

class VehicleModule(BaseModule):
    """
    A longitudinal dynamics model calculating acceleration and velocity based on traction, 
    aerodynamic drag, rolling resistance, and braking.
    """
    def __init__(self, initial_state: VehicleState):
        """
        Initializes the vehicle with default efficiency and friction coefficients.
        """
        self.state = initial_state
        self.drivetrain_efficiency = 0.9
        self.rolling_resistance = 0.015
        self.load_scale = 5000.0 

    def apply_config(self, cfg: VehicleSpecification):
        """
        Configures physical dimensions and constraints like mass, wheel radius, and tire grip.
        """
        self.spec = cfg
        self.state.mass_kg = cfg.mass_kg
        self.wheel_radius = cfg.wheel_radius_m
        self.tire_grip_coefficient = getattr(cfg, 'tire_grip', 1.0)
        self.max_tire_force = self.state.mass_kg * 9.81 * self.tire_grip_coefficient

    def update(self, dt: float):
        """
        Performs physics integration for the current time step using the sum of all longitudinal forces.
        """
        i = self.input
        s = self.state

        total_mass = s.mass_kg + i.cargo_mass_kg
        v_mps = s.speed_kmh / 3.6

        # 1. Traction Force: Torque delivered to the contact patch, capped by tire grip
        wheel_torque = i.torque_nm * i.gear_ratio * self.drivetrain_efficiency
        wheel_force_raw = wheel_torque / max(0.01, self.wheel_radius)
        wheel_force = max(-self.max_tire_force, min(self.max_tire_force, wheel_force_raw))

        # 2. Aerodynamic Drag: Square of velocity multiplied by frontal area and drag coefficient
        drag = 0.5 * 1.225 * self.spec.drag_coefficient * self.spec.frontal_area * v_mps**2
        
        # 3. Rolling Resistance: Opposes motion based on mass and gravity
        roll_max = self.rolling_resistance * total_mass * 9.81
        if abs(v_mps) < 0.1:
            roll = min(abs(wheel_force), roll_max) * (1 if wheel_force > 0 else -1)
        else:
            roll = roll_max * (1 if v_mps > 0 else -1)

        # 4. Incline Force: Component of gravity acting along the longitudinal axis
        slope_force = total_mass * 9.81 * (i.road_incline_pct / 100.0)

        # Base net force before braking
        net_force = wheel_force - drag - roll - slope_force

        # 5. Braking Logic: Applies negative force against the direction of movement
        brake_force_max = total_mass * 10.0 # Standardized max decel ~1.0g
        applied_brake_force = i.brake * brake_force_max

        if abs(v_mps) > 0.05:
            net_force -= applied_brake_force * (1 if v_mps > 0 else -1)
        elif i.brake > 0.05:
            # Static braking to keep the car stationary on inclines
            if abs(net_force) < applied_brake_force:
                net_force = 0
            else:
                net_force -= applied_brake_force * (1 if net_force > 0 else -1)

        # 6. Motion Integration (Newton's Second Law)
        acc = net_force / total_mass
        s.acc_mps2 = acc
        
        new_v_mps = v_mps + acc * dt
        
        # Prevent oscillation around zero speed caused by discrete time steps
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