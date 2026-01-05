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


@dataclass
class GearboxInput(BaseInput):
    engine_rpm: float
    throttle: float
    vehicle_speed: float

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

        # konfigurowalne
        # gear_ratios powinny być bez final_drive; final_drive ustawiamy jako osobny parametr
        self.gear_ratios = {}   # będzie ustawiane z profilu
        self.final_drive = 1.0

        self.shift_timer = 0.0
        self.shift_delay = 0.4
        self.shift_cooldown = 0.3

        self.engine_max_rpm = 9000   # ustawiane z profilu w main.py
        self._target_gear = initial_state.current_gear

    def apply_config(self, cfg: GearboxSpecification):
        self.final_drive = cfg.final_drive
        self.gear_ratios = {i+1: g for i, g in enumerate(cfg.gears)}

        self.upshift_rpm = cfg.upshift_rpm
        self.downshift_rpm = cfg.downshift_rpm
        self.shift_delay = cfg.shift_delay


    def update(self, dt: float):
        i = self.input
        s = self.state

        base = self.gear_ratios.get(s.current_gear, 1.0)
        s.gear_ratio = base * self.final_drive

        max_gear = max(self.gear_ratios.keys())

        target_gear = s.current_gear

        if i.engine_rpm >= self.upshift_rpm and s.current_gear < max_gear:
            target_gear += 1

        elif i.engine_rpm <= self.downshift_rpm and s.current_gear > 1:
            target_gear -= 1

        # wykonaj zmianę NATYCHMIAST
        if target_gear != s.current_gear:
            s.current_gear = target_gear
            s.shift_event = True
        else:
            s.shift_event = False

        # aktualizacja przełożenia po zmianie
        base = self.gear_ratios.get(s.current_gear, 1.0)
        s.gear_ratio = base * self.final_drive

        self.output = GearboxOutput(
            current_gear=s.current_gear,
            gear_ratio=s.gear_ratio,
            shift_event=s.shift_event
        )
