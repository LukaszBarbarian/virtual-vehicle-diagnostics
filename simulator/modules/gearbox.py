# gearbox.py
from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
from simulator.core.models.model_specification import GearboxSpecification

@dataclass
class GearboxState(BaseState):
    current_gear: int
    gear_ratio: float
    gearbox_temp_c: float
    shift_event: bool
    last_speed: float = 0.0
    preparing_shift: bool = False
    shifting: bool = False



@dataclass
class GearboxInput(BaseInput):
    engine_rpm: float
    throttle: float
    vehicle_speed: float
    throttle_rate: float


@dataclass
class GearboxOutput(BaseOutput):
    current_gear: int
    gear_ratio: float
    shift_event: bool

class GearboxModule(BaseModule):
    def __init__(self, initial_state: GearboxState):
        self.state = initial_state
        self.input = None
        self.output = None

        self.gear_ratios = {}
        self.final_drive = 1.0

        self.shift_timer = 0.0
        self.shift_delay = 0.4
        self.shift_cooldown = 0.3
        self.shift_cooldown_timer = 0.0

        self.engine_max_rpm = 9000
        self._target_gear = initial_state.current_gear
        self.actual_shift_time = 0.15   # realne rozłączenie sprzęgła (DCT)


    def apply_config(self, cfg: GearboxSpecification):
        self.final_drive = cfg.final_drive
        self.gear_ratios = {i+1: g for i, g in enumerate(cfg.gears)}
        self.upshift_rpm = cfg.upshift_rpm
        self.downshift_rpm = cfg.downshift_rpm
        self.shift_delay = cfg.shift_delay

    def update(self, dt: float):
        i = self.input
        s = self.state

        max_gear = max(self.gear_ratios.keys())

        # ======================================================
        # 1️⃣ FAKTYCZNY SHIFT (sprzęgło ROZŁĄCZONE)
        # ======================================================
        if s.shifting:
            self.shift_timer -= dt
            s.shift_event = True  # sprzęgło OFF

            if self.shift_timer <= 0.0:
                # finalizacja zmiany biegu
                s.current_gear = self._target_gear
                s.shifting = False
                s.shift_event = False
                self.shift_timer = 0.0
                self.shift_cooldown_timer = self.shift_cooldown

            base = self.gear_ratios.get(s.current_gear, 1.0)
            s.gear_ratio = base * self.final_drive

            self.output = GearboxOutput(
                current_gear=s.current_gear,
                gear_ratio=s.gear_ratio,
                shift_event=s.shift_event
            )
            return

        # ======================================================
        # 2️⃣ OCZEKIWANIE NA SHIFT (sprzęgło WCIĄŻ POŁĄCZONE)
        # ======================================================
        if s.preparing_shift:
            self.shift_timer -= dt

            if self.shift_timer <= 0.0:
                # TERAZ zaczynamy faktyczny shift
                s.preparing_shift = False
                s.shifting = True
                self.shift_timer = self.actual_shift_time

            # wciąż normalna jazda, sprzęgło ON
            base = self.gear_ratios.get(s.current_gear, 1.0)
            s.gear_ratio = base * self.final_drive

            self.output = GearboxOutput(
                current_gear=s.current_gear,
                gear_ratio=s.gear_ratio,
                shift_event=False
            )
            return

        # ======================================================
        # 3️⃣ COOLDOWN PO ZMIANIE BIEGU
        # ======================================================
        if self.shift_cooldown_timer > 0.0:
            self.shift_cooldown_timer -= dt

        # ======================================================
        # 4️⃣ DETEKCJA POTRZEBY ZMIANY BIEGU
        # ======================================================
        target_gear = s.current_gear

        target_gear = s.current_gear

        # UPSHIFT
        if (
            i.engine_rpm >= self.upshift_rpm
            and s.current_gear < max_gear
            and self.shift_cooldown_timer <= 0.0
        ):
            target_gear += 1

        # DOWNSHIFT (RPM)
        if (
            i.engine_rpm <= self.downshift_rpm
            and s.current_gear > 1
            and self.shift_cooldown_timer <= 0.0
        ):
            target_gear -= 1
            

        # KICKDOWN (override)
        if (
            i.throttle_rate > 0.8
            and s.current_gear > 1
            and self.shift_cooldown_timer <= 0.0
        ):
            target_gear -= 1

        # ======================================================
        # 5️⃣ DECYZJA O ZMIANIE (ALE BEZ RUSZANIA SPRZĘGŁA)
        # ======================================================
        if target_gear != s.current_gear:
            self._target_gear = target_gear
            self.shift_timer = self.shift_delay
            s.preparing_shift = True
            s.shift_event = False
        else:
            s.shift_event = False

        # ======================================================
        # 6️⃣ NORMALNA JAZDA
        # ======================================================
        base = self.gear_ratios.get(s.current_gear, 1.0)
        s.gear_ratio = base * self.final_drive

        self.output = GearboxOutput(
            current_gear=s.current_gear,
            gear_ratio=s.gear_ratio,
            shift_event=False
        )
