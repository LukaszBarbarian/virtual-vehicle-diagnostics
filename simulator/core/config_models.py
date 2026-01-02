from dataclasses import dataclass
from typing import List

@dataclass
class EngineConfig:
    max_rpm: float
    idle_rpm: float
    base_torque_nm: float
    peak_rpm: float
    max_power_kw: float
    rotational_inertia: float
    efficiency: float

    bsfc: float
    heat_fraction: float

    rpm_response: float
    shift_rpm_drop_rate: float
    torque_curve_min: float
    limiter_start_ratio: float
    limiter_torque_factor: float    


@dataclass
class GearboxConfig:
    final_drive: float
    gears: List[float]
    upshift_rpm: float
    downshift_rpm: float
    shift_delay: float


@dataclass
class VehicleConfig:
    mass_kg: float
    drag_coefficient: float
    rolling_resistance: float
    frontal_area: float
    wheel_radius_m: float
    drivetrain_efficiency: float
    brake_force_max: float
    load_scale: float


@dataclass
class ThermalConfig:
    thermostat_open_temp: float
    fan_on_temp: float
    fan_off_temp: float

    airflow_coeff: float
    cooling_coeff: float
    heat_to_coolant_ratio: float
    oil_response_rate: float
    thermal_mass: float

@dataclass
class DriverConfig:
    ramp_time: float
    cruise_throttle: float
    cruise_time: float
    decel_time: float
    final_throttle: float
    driver_style: str


@dataclass
class CarConfig:
    name: str
    engine: EngineConfig
    gearbox: GearboxConfig
    vehicle: VehicleConfig
    thermal: ThermalConfig
    driver: DriverConfig
