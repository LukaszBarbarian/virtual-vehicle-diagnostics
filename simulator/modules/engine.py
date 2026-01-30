from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
import math
from simulator.core.models.model_specification import EngineSpecification

@dataclass
class EngineInput(BaseInput):
    """
    Physical inputs for the engine module, including control signals and drivetrain feedback.
    """
    throttle: float
    current_gear: int
    vehicle_speed: float
    ambient_temp_c: float
    cooling_efficiency: float
    torque_loss_factor: float
    clutch_factor: float
    gear_ratio_total: float
    vehicle_mass_kg: float
    vehicle_acc_mps2: float
    wheel_radius_m: float = 0.34

@dataclass
class EngineOutput(BaseOutput):
    """
    Engine output telemetry and forces generated for the drivetrain.
    """
    torque_nm: float
    wheel_force_n: float
    fuel_rate_lph: float
    heat_kw: float
    engine_rpm: float
    fuel_l_per_100km: float

@dataclass
class EngineState(BaseState):
    """
    Internal state of the engine, tracking temperatures, rotation, and fuel consumption.
    """
    engine_rpm: float
    engine_temp_c: float
    oil_temp_c: float
    efficiency: float
    fuel_rate_lph: float = 0.0
    engine_torque_filtered: float = 0.0
    internal_friction_nm: float = 0.0
    rotational_inertia: float = 0.08

class EngineModule(BaseModule):
    """
    Simulates internal combustion engine physics, including torque curves, 
    engine braking, anti-stall logic, and fuel consumption.
    """
    def __init__(self, initial_state: EngineState):
        """
        Initializes the engine module with a state and default idle parameters.
        """
        self.state = initial_state
        self.spec: EngineSpecification = None
        self.idle_rpm = 800.0

    def apply_config(self, cfg: EngineSpecification):
        """
        Configures engine limits and performance characteristics based on the provided specification.
        """
        self.spec = cfg
        self.max_rpm = getattr(cfg, 'max_rpm', 7000.0)
        self.max_torque = (
            getattr(cfg, 'max_torque', None) or 
            getattr(cfg, 'peak_torque', None) or 
            getattr(cfg, 'torque_nm', 300.0)
        )
        self.max_power_rpm = (
            getattr(cfg, 'max_power_rpm', None) or 
            getattr(cfg, 'power_rpm', self.max_rpm * 0.85)
        )
        self.state.rotational_inertia = getattr(cfg, 'rotational_inertia', 0.08)

    def _get_max_torque_at_rpm(self, rpm: float) -> float:
        """
        Calculates the theoretical maximum torque available at a given RPM using a parabolic torque curve.
        """
        peak_t_rpm = self.max_power_rpm * 0.75
        rpm_range = self.max_rpm - self.idle_rpm
        x = (rpm - peak_t_rpm) / max(1.0, rpm_range)
        torque_curve = 1.0 - (x**2 * 1.5)
        return max(0.0, self.max_torque * torque_curve)

    def _get_losses(self, rpm: float, throttle: float) -> float:
        """
        Calculates combined internal losses including friction and pumping losses (engine braking).
        """
        friction = (self.max_torque * 0.04) + (rpm / self.max_rpm) * (self.max_torque * 0.08)
        pumping_loss = (1.0 - throttle) * (rpm / self.max_rpm) * (self.max_torque * 0.22)
        return friction + pumping_loss

    def update(self, dt: float):
        """
        Main physics update loop. Handles RPM synchronization, torque generation, and fuel logic.
        """
        i = self.input
        s = self.state
        effective_throttle = i.throttle 
        
        # RPM Logic: Synchronize with wheels if clutch is engaged, otherwise simulate free-revving
        if i.clutch_factor > 0.8 and i.gear_ratio_total > 0:
            v_mps = i.vehicle_speed / 3.6
            wheel_rps = v_mps / (2 * math.pi * max(0.01, i.wheel_radius_m))
            target_rpm = wheel_rps * i.gear_ratio_total * 60
            s.engine_rpm = max(self.idle_rpm, min(self.max_rpm, target_rpm))
        else:
            angular_accel = (s.engine_torque_filtered / max(0.01, s.rotational_inertia))
            rpm_change = (angular_accel * (60 / (2 * math.pi))) * dt
            s.engine_rpm = max(0.0, min(self.max_rpm + 500, s.engine_rpm + rpm_change))

        # Torque Calculation
        max_t = self._get_max_torque_at_rpm(s.engine_rpm) * (1.0 - i.torque_loss_factor)
        s.internal_friction_nm = self._get_losses(s.engine_rpm, effective_throttle)
        
        # Anti-Stall & Creep Logic
        creep_torque = self.max_torque * 0.12
        idle_torque_request = creep_torque if i.current_gear > 0 else 0.0

        if s.engine_rpm < self.idle_rpm:
            idle_torque_request += (self.idle_rpm - s.engine_rpm) * 6.0
            
        # Combine throttle torque with responsiveness boost
        throttle_torque = max_t * effective_throttle
        if effective_throttle > 0.01:
            throttle_torque += max_t * 0.05 

        # Net Torque filtering for smooth response
        raw_net_torque = throttle_torque + idle_torque_request - s.internal_friction_nm
        alpha = min(1.0, 0.85 * (dt / 0.01))
        s.engine_torque_filtered += (raw_net_torque - s.engine_torque_filtered) * alpha

        # Performance, Fuel and Thermal simulation
        omega = s.engine_rpm * 2 * math.pi / 60
        output_power_kw = (s.engine_torque_filtered * omega) / 1000.0
        
        # Fuel Cut-Off during engine braking
        if s.engine_torque_filtered < 0 and s.engine_rpm > self.idle_rpm + 200:
            s.fuel_rate_lph = 0.0
        else:
            total_indicated_power_kw = max(0.0, output_power_kw + (s.internal_friction_nm * omega / 1000.0))
            fuel_lph = 1.2 + (total_indicated_power_kw * 0.22)
            s.fuel_rate_lph = min(600.0, fuel_lph)

        # Thermal evolution based on load
        target_temp = 90.0 + (effective_throttle * 25.0)
        s.engine_temp_c += (target_temp - s.engine_temp_c) * (0.02 * dt / 0.01)

        self.output = EngineOutput(
            torque_nm=round(s.engine_torque_filtered, 2),
            engine_rpm=round(s.engine_rpm, 2),
            fuel_rate_lph=round(s.fuel_rate_lph, 2),
            heat_kw=round(max(0.0, output_power_kw * 1.5), 2),
            wheel_force_n=0.0,
            fuel_l_per_100km=0.0
        )