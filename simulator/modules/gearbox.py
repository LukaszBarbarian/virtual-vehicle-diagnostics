from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
from simulator.core.models.model_specification import GearboxSpecification

@dataclass
class GearboxState(BaseState):
    """
    Internal state of the gearbox tracking the current gear, ratios, and the shifting process status.
    """
    current_gear: int
    gear_ratio: float
    gearbox_temp_c: float
    shift_event: bool
    last_speed: float = 0.0
    preparing_shift: bool = False
    shifting: bool = False

@dataclass
class GearboxInput(BaseInput):
    """
    Input signals required for gearbox automation, including engine feedback and driver intent.
    """
    engine_rpm: float
    throttle: float
    vehicle_speed: float
    throttle_rate: float

@dataclass
class GearboxOutput(BaseOutput):
    """
    Resulting gearbox state broadcast to the engine and vehicle modules.
    """
    current_gear: int
    gear_ratio: float
    shift_event: bool

class GearboxModule(BaseModule):
    """
    Simulates an automatic transmission with programmable shift points, shift delays, and clutch synchronization.
    """
    def __init__(self, initial_state: GearboxState):
        """
        Initializes the gearbox with state and internal timers for shift management.
        """
        self.state = initial_state
        self.shift_timer = 0.0
        self.shift_cooldown_timer = 0.0
        self._target_gear = initial_state.current_gear

    def apply_config(self, cfg: GearboxSpecification):
        """
        Maps the technical specification to internal ratios and shift thresholds.
        """
        self.spec = cfg
        self.final_drive = cfg.final_drive
        self.gear_ratios = {i+1: g for i, g in enumerate(cfg.gears)}
        self.upshift_rpm = cfg.upshift_rpm
        self.downshift_rpm = cfg.downshift_rpm
        self.shift_delay = cfg.shift_delay
        self.actual_shift_time = getattr(cfg, 'actual_shift_time', 0.15)
        self.shift_cooldown = 0.5

    def update(self, dt: float):
        """
        Main logic loop handling the state machine for gear selection and mechanical transitions.
        """
        i = self.input
        s = self.state

        if self.shift_cooldown_timer > 0:
            self.shift_cooldown_timer -= dt

        # Stage 1: Shifting (Clutch is disengaged, mechanical gear swap)
        if s.shifting:
            self.shift_timer -= dt
            s.shift_event = True
            if self.shift_timer <= 0:
                s.current_gear = self._target_gear
                s.shifting = False
                s.shift_event = False
                self.shift_cooldown_timer = self.shift_cooldown
        
        # Stage 2: Preparation (Decision made, driver/system preparing for shift)
        elif s.preparing_shift:
            self.shift_timer -= dt
            if self.shift_timer <= 0:
                s.preparing_shift = False
                s.shifting = True
                self.shift_timer = self.actual_shift_time
        
        # Stage 3: Decision Logic (Monitoring RPM and kickdown triggers)
        else:
            target = s.current_gear
            if i.engine_rpm > self.upshift_rpm and s.current_gear < max(self.gear_ratios.keys()):
                target += 1
            elif (i.engine_rpm < self.downshift_rpm or (i.throttle_rate > 0.8 and i.throttle > 0.7)) and s.current_gear > 1:
                target -= 1
            
            if target != s.current_gear and self.shift_cooldown_timer <= 0:
                self._target_gear = target
                self.shift_timer = self.shift_delay
                s.preparing_shift = True

        # Compute the final mechanical advantage
        base_ratio = self.gear_ratios.get(s.current_gear, 0.0)
        s.gear_ratio = base_ratio * self.final_drive

        self.output = GearboxOutput(
            current_gear=s.current_gear,
            gear_ratio=s.gear_ratio,
            shift_event=s.shift_event
        )