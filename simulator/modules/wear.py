from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
import math
from simulator.core.models.model_specification import WearSpecification

@dataclass
class WearState(BaseState):
    """
    State representing the current degradation of vehicle components.
    """
    engine_wear: float = 0.0             # 0..1 (1.0 = failure)
    gearbox_wear: float = 0.0            # 0..1
    cooling_efficiency_loss: float = 0.0
    torque_loss_factor: float = 0.0

@dataclass
class WearInput(BaseInput):
    """
    Environmental and operational data affecting the rate of component degradation.
    """
    engine_temp_c: float
    oil_temp_c: float
    load: float                          # 0..1 normalized load
    engine_rpm: float
    gearbox_temp_c: float
    throttle_rate: float                 # Normalized rate of change
    is_shifting: bool = False            # Tracks gearbox mechanical stress

@dataclass
class WearOutput(BaseOutput):
    """
    Impact of cumulative wear on vehicle performance and health status.
    """
    cooling_efficiency: float
    torque_loss_factor: float
    health_status: float                 # 1.0 (New) to 0.0 (Failed)

class WearModule(BaseModule):
    """
    Simulates vehicle component wear and performance degradation based on 
    operating temperatures, RPM abuse, and load history.
    """

    def __init__(self, initial_state: WearState):
        """
        Initializes the wear module with a state and internal fatigue counters.
        """
        self.state = initial_state
        self.input = None
        self.output = None
        self.fatigue = 0.0
        
        # Default calibration values (overwritten by apply_config)
        self.temp_threshold = 95.0
        self.thermal_stress_factor = 0.0002
        self.load_stress_factor = 0.0001
        self.rpm_threshold = 4500.0
        self.rpm_stress_factor = 0.000001
        self.cooling_degradation_scale = 0.4
        self.torque_degradation_scale = 0.35
        self.wear_time_scale = 100.0 

    def apply_config(self, spec: WearSpecification):
        """
        Configures the wear sensitivity parameters based on the specific vehicle type.
        """
        self.temp_threshold = spec.temp_threshold
        self.thermal_stress_factor = spec.thermal_stress_factor
        self.load_stress_factor = spec.load_stress_factor
        self.rpm_threshold = spec.rpm_threshold
        self.rpm_stress_factor = spec.rpm_stress_factor
        self.cooling_degradation_scale = spec.cooling_degradation_scale
        self.torque_degradation_scale = spec.torque_degradation_scale
        self.wear_time_scale = spec.wear_time_scale

    def update(self, dt: float):
        """
        Calculates cumulative damage impulses from thermal and mechanical stress.
        """
        if self.input is None or dt <= 0:
            return

        i = self.input
        s = self.state
        effective_dt = dt * self.wear_time_scale
        engine_impulse = 0.0

        # 1. Cold Engine Thermal Stress (Damage caused by high load before reaching operating temp)
        if i.oil_temp_c < self.temp_threshold:
            cold_ratio = (self.temp_threshold - i.oil_temp_c) / self.temp_threshold
            engine_impulse += (cold_ratio ** 2) * i.load * self.thermal_stress_factor

        # 2. Overheating Abuse (Extreme oil temperatures exceeding 120'C)
        if i.oil_temp_c > 120.0:
            hot_delta = i.oil_temp_c - 120.0
            engine_impulse += (hot_delta * 0.1) * self.thermal_stress_factor

        # 3. High RPM Mechanical Stress (Damage increases quadratically above threshold)
        rpm_ratio = i.engine_rpm / max(1.0, self.rpm_threshold)
        if rpm_ratio > 1.0:
            excess = rpm_ratio - 1.0
            engine_impulse += (excess ** 2) * self.rpm_stress_factor

        # 4. Natural Baseline Aging
        engine_impulse += (i.load * 1e-6) + 1e-8

        # Update state with integrated damage
        s.engine_wear = min(1.0, s.engine_wear + (engine_impulse * effective_dt))

        # Calculate performance penalties
        self.output = WearOutput(
            cooling_efficiency=max(0.1, 1.0 - (s.engine_wear * self.cooling_degradation_scale)),
            torque_loss_factor=min(0.5, s.engine_wear * self.torque_degradation_scale),
            health_status=1.0 - s.engine_wear
        )