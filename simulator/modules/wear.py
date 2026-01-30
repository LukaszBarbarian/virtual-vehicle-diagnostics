from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
import math

from simulator.core.models.model_specification import WearSpecification

# =========================
# STATE
# =========================
@dataclass
class WearState(BaseState):
    """
    State representing the current degradation of vehicle components.
    """
    engine_wear: float = 0.0             # 0..1 (1.0 = failure)
    gearbox_wear: float = 0.0            # 0..1
    cooling_efficiency_loss: float = 0.0
    torque_loss_factor: float = 0.0


# =========================
# INPUT
# =========================
@dataclass
class WearInput(BaseInput):
    """
    Environmental and operational data affecting wear.
    """
    engine_temp_c: float
    oil_temp_c: float
    load: float                # 0..1
    engine_rpm: float
    gearbox_temp_c: float
    throttle_rate: float       # -1..1 (rate of change)
    is_shifting: bool = False  # Added to track gearbox stress


# =========================
# OUTPUT
# =========================
@dataclass
class WearOutput(BaseOutput):
    """
    Impact of wear on vehicle performance.
    """
    cooling_efficiency: float
    torque_loss_factor: float
    health_status: float       # 1.0 (New) to 0.0 (Dead)


# =========================
# MODULE
# =========================
class WearModule(BaseModule):
    """
    Generic wear simulation module. 
    Can be configured for different vehicles (e.g., Focus vs Lamborghini) 
    via injected configuration object.
    """

    def __init__(self, initial_state: WearState):
        self.state = initial_state
        self.input = None
        self.output = None
        self.fatigue = 0.0
        
        # Defaults (overwritten by apply_config)
        self.temp_threshold = 95.0
        self.thermal_stress_factor = 0.0002
        self.load_stress_factor = 0.0001
        self.rpm_threshold = 4500.0
        self.rpm_stress_factor = 0.000001
        self.cooling_degradation_scale = 0.4
        self.torque_degradation_scale = 0.35
        self.wear_time_scale = 100.0 

    def apply_config(self, spec: WearSpecification):
        self.temp_threshold = spec.temp_threshold
        self.thermal_stress_factor = spec.thermal_stress_factor
        self.load_stress_factor = spec.load_stress_factor
        self.rpm_threshold = spec.rpm_threshold
        self.rpm_stress_factor = spec.rpm_stress_factor
        self.cooling_degradation_scale = spec.cooling_degradation_scale
        self.torque_degradation_scale = spec.torque_degradation_scale
        self.wear_time_scale = spec.wear_time_scale

    def update(self, dt: float):
        if self.input is None or dt <= 0:
            return

        i = self.input
        s = self.state
        effective_dt = dt * self.wear_time_scale
        engine_impulse = 0.0

        # --- 1. Thermal Stress (Cold engine) ---
        if i.oil_temp_c < self.temp_threshold:
            cold_ratio = (self.temp_threshold - i.oil_temp_c) / self.temp_threshold
            # Dodajemy i.load, żeby na jałowym (load=0) zużycie było znikome
            engine_impulse += (cold_ratio ** 2) * i.load * self.thermal_stress_factor

        # --- 2. High Oil Temp Abuse (Olej > 120'C) ---
        if i.oil_temp_c > 120.0:
            hot_delta = i.oil_temp_c - 120.0
            engine_impulse += (hot_delta * 0.1) * self.thermal_stress_factor

        # --- 3. RPM Stress ---
        rpm_ratio = i.engine_rpm / max(1.0, self.rpm_threshold)
        if rpm_ratio > 1.0:
            excess = rpm_ratio - 1.0
            # Wykładniczo, ale bez przesadnych mnożników w kodzie
            engine_impulse += (excess ** 2) * self.rpm_stress_factor

        # --- 4. Baseline (Bardzo mały, by trend nie stał w miejscu) ---
        # 1e-6 oznacza, że potrzeba miliona sekund (bez stresu), by zniszczyć silnik
        engine_impulse += (i.load * 1e-6) + 1e-8

        # --- Apply to State ---
        # s.engine_wear rośnie teraz wolniej
        s.engine_wear = min(1.0, s.engine_wear + (engine_impulse * effective_dt))

        # --- Final Outputs ---
        self.output = WearOutput(
            cooling_efficiency=max(0.1, 1.0 - (s.engine_wear * self.cooling_degradation_scale)),
            torque_loss_factor=min(0.5, s.engine_wear * self.torque_degradation_scale),
            health_status=1.0 - s.engine_wear
        )