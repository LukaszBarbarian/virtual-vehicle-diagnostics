from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput


# ============================================================
# STATE / INPUT / OUTPUT
# ============================================================

@dataclass
class WearState(BaseState):
    engine_wear: float                  # 0.0 → 1.0
    gearbox_wear: float                 # (na razie pasywny)
    cooling_efficiency_loss: float      # 0.0 → 1.0
    torque_loss_factor: float           # 0.0 → 1.0


@dataclass
class WearInput(BaseInput):
    engine_temp_c: float
    oil_temp_c: float
    load: float                         # 0.0 → 1.0
    engine_rpm: float
    gearbox_temp_c: float


@dataclass
class WearOutput(BaseOutput):
    cooling_efficiency: float           # 0.0 → 1.0
    torque_loss_factor: float           # 0.0 → 1.0


# ============================================================
# WEAR MODULE
# ============================================================

class WearModule(BaseModule):
    """
    Deterministic engine wear model.

    Design goals:
    - wear always increases (monotonic)
    - base wear is smooth
    - extreme conditions create sharp spikes
    - worn engine degrades faster (non-linear escalation)
    - no randomness (ML-friendly)
    """

    def __init__(self, initial_state: WearState):
        self.state = initial_state
        self.input: WearInput | None = None
        self.output: WearOutput | None = None

    # --------------------------------------------------------
    # CONFIG
    # --------------------------------------------------------

    def apply_config(self, cfg):
        # thresholds
        self.temp_threshold = cfg.temp_threshold              # e.g. 90°C
        self.rpm_threshold = cfg.rpm_threshold                # e.g. 4500 RPM

        # linear stress factors
        self.thermal_stress_factor = cfg.thermal_stress_factor
        self.load_stress_factor = cfg.load_stress_factor
        self.rpm_stress_factor = cfg.rpm_stress_factor

        # degradation scaling
        self.cooling_degradation_scale = cfg.cooling_degradation_scale
        self.torque_degradation_scale = cfg.torque_degradation_scale

        # spike tuning (hardcoded on purpose – deterministic)
        self.thermal_spike_offset = 20.0      # °C above threshold
        self.thermal_spike_scale = 0.0001

        self.rpm_spike_multiplier = 1.1       # 110% rpm_threshold

    # --------------------------------------------------------
    # UPDATE
    # --------------------------------------------------------

    def update(self, dt: float):
        if self.input is None:
            return

        i = self.input
        s = self.state

        # -------------------------------
        # BASE LINEAR STRESS
        # -------------------------------

        thermal_stress = max(
            0.0,
            i.engine_temp_c - self.temp_threshold
        ) * self.thermal_stress_factor

        load_stress = i.load * self.load_stress_factor

        rpm_stress = max(
            0.0,
            i.engine_rpm - self.rpm_threshold
        ) * self.rpm_stress_factor

        # -------------------------------
        # THERMAL SPIKE (OVERHEAT EVENTS)
        # -------------------------------

        thermal_spike = 0.0
        if i.engine_temp_c > self.temp_threshold + self.thermal_spike_offset:
            delta = i.engine_temp_c - (self.temp_threshold + self.thermal_spike_offset)
            thermal_spike = (delta ** 2) * self.thermal_spike_scale

        # -------------------------------
        # RPM SPIKE (AGGRESSIVE DRIVING)
        # -------------------------------

        rpm_spike = 0.0
        rpm_spike_threshold = self.rpm_threshold * self.rpm_spike_multiplier
        if i.engine_rpm > rpm_spike_threshold:
            delta = i.engine_rpm - rpm_spike_threshold
            rpm_spike = (delta ** 2) * self.rpm_stress_factor

        # -------------------------------
        # NON-LINEAR WEAR ESCALATION
        # -------------------------------

        # worn engines degrade faster
        wear_multiplier = 1.0 + (s.engine_wear ** 2) * 2.0

        # -------------------------------
        # TOTAL WEAR INCREMENT
        # -------------------------------

        delta_wear = (
            thermal_stress
            + load_stress
            + rpm_stress
            + thermal_spike
            + rpm_spike
        ) * wear_multiplier * dt

        # monotonic clamp
        s.engine_wear = min(1.0, s.engine_wear + delta_wear)

        # -------------------------------
        # DERIVED EFFECTS
        # -------------------------------

        s.cooling_efficiency_loss = min(
            1.0,
            s.engine_wear * self.cooling_degradation_scale
        )

        s.torque_loss_factor = min(
            1.0,
            s.engine_wear * self.torque_degradation_scale
        )

        # -------------------------------
        # OUTPUT
        # -------------------------------

        self.output = WearOutput(
            cooling_efficiency=1.0 - s.cooling_efficiency_loss,
            torque_loss_factor=s.torque_loss_factor
        )
