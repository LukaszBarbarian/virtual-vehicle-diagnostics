from dataclasses import dataclass
from typing import List

@dataclass
class EngineSpecification:
    """
    Technical parameters defining engine performance, torque characteristics, and efficiency.
    """
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
class GearboxSpecification:
    """
    Transmission settings including gear ratios, shift points, and mechanical delays.
    """
    final_drive: float
    gears: List[float]
    upshift_rpm: float
    downshift_rpm: float
    shift_delay: float

@dataclass
class WearSpecification:
    """
    Stress factors and thresholds determining the degradation rate of mechanical components.
    """
    temp_threshold: float
    thermal_stress_factor: float
    load_stress_factor: float
    rpm_threshold: float
    rpm_stress_factor: float
    cooling_degradation_scale: float
    torque_degradation_scale: float
    wear_time_scale: float

@dataclass
class VehicleSpecification:
    """
    Physical properties of the vehicle including aerodynamics, mass, and drivetrain efficiency.
    """
    mass_kg: float
    drag_coefficient: float
    rolling_resistance: float
    frontal_area: float
    wheel_radius_m: float
    drivetrain_efficiency: float
    brake_force_max: float
    load_scale: float

@dataclass
class ThermalSpecification:
    """
    Thermodynamic properties and cooling system thresholds for engine and oil management.
    """
    thermostat_open_temp: float
    fan_on_temp: float
    fan_off_temp: float
    airflow_coeff: float
    cooling_coeff: float
    heat_to_coolant_ratio: float
    oil_response_rate: float
    thermal_mass: float

@dataclass
class DriverSpecification:
    """
    Behavioral parameters defining how the simulated driver interacts with throttle and brakes.
    """
    ramp_time: float
    cruise_throttle: float
    cruise_time: float
    decel_time: float
    final_throttle: float
    driver_style: str

@dataclass
class CarSpecification:
    """
    Top-level container grouping all individual mechanical and thermal subsystems of a car.
    """
    name: str
    engine: EngineSpecification
    gearbox: GearboxSpecification
    vehicle: VehicleSpecification
    thermal: ThermalSpecification

@dataclass
class EnvironmentSpecification:
    """
    External conditions affecting the simulation, such as ambient temperature and road geometry.
    """
    ambient_temp: float
    road_incline: float