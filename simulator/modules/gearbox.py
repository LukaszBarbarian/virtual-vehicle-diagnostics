from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
from simulator.core.models.model_specification import GearboxSpecification

# Shift map of an automatic gearbox, as fractions of the car's upshift_rpm:
# (upshift at light pedal, upshift at full pedal, downshift at light pedal, downshift at full pedal).
# Eco changes up early to keep revs low, sport holds gears close to the redline.
SHIFT_MAPS = {
    "eco": (0.30, 0.70, 0.20, 0.28),
    "normal": (0.37, 0.87, 0.23, 0.33),
    "sport": (0.50, 1.00, 0.30, 0.40),
}

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
    pedal: float | None = None          # driver's pedal position; the shift map reads this
    shift_mode: str = "normal"          # eco / normal / sport, from the driver profile

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
        self._last_rpm = 0.0

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
        # Never plan a downshift below this: the engine would lug just above idle
        self.idle_floor_rpm = 1100.0

    def shift_points(self, pedal: float, mode: str) -> tuple[float, float]:
        """
        Upshift and downshift RPM for the current pedal position and driving mode: light pedal
        changes up early, full pedal holds the gear towards the car's upshift_rpm.
        """
        up_lo, up_hi, down_lo, down_hi = SHIFT_MAPS.get(mode, SHIFT_MAPS["normal"])
        p = max(0.0, min(1.0, pedal))
        up = self.upshift_rpm * (up_lo + (up_hi - up_lo) * p)
        down = self.upshift_rpm * (down_lo + (down_hi - down_lo) * p)
        return up, max(down, self.idle_floor_rpm)

    def _rpm_after_shift(self, rpm: float, gear: int) -> float:
        current = self.gear_ratios.get(self.state.current_gear, 1.0)
        return rpm * self.gear_ratios.get(gear, current) / current

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

        # Stage 3: Decision Logic (shift map + kickdown, with protection against shift hunting)
        else:
            target = s.current_gear
            up_rpm, down_rpm = self.shift_points(i.pedal if i.pedal is not None else i.throttle, i.shift_mode)
            top_gear = max(self.gear_ratios.keys())
            kickdown = i.throttle_rate > 0.8 and i.throttle > 0.7

            # Like a real transmission controller, look ahead to the RPM at the end of the shift
            rpm_rate = (i.engine_rpm - self._last_rpm) / dt if dt > 0 else 0.0
            projected_rpm = i.engine_rpm + max(0.0, rpm_rate) * (self.shift_delay + self.actual_shift_time)

            if projected_rpm > up_rpm and s.current_gear < top_gear:
                # Only change up if the engine would not fall straight below the downshift point
                if self._rpm_after_shift(i.engine_rpm, s.current_gear + 1) > down_rpm * 1.15:
                    target += 1
            elif (i.engine_rpm < down_rpm or kickdown) and s.current_gear > 1:
                # Only change down if the engine would not land straight above the upshift point
                if self._rpm_after_shift(i.engine_rpm, s.current_gear - 1) < up_rpm * 0.95:
                    target -= 1

            if target != s.current_gear and self.shift_cooldown_timer <= 0:
                self._target_gear = target
                self.shift_timer = self.shift_delay
                s.preparing_shift = True

        self._last_rpm = i.engine_rpm

        # Compute the final mechanical advantage
        base_ratio = self.gear_ratios.get(s.current_gear, 0.0)
        s.gear_ratio = base_ratio * self.final_drive

        self.output = GearboxOutput(
            current_gear=s.current_gear,
            gear_ratio=s.gear_ratio,
            shift_event=s.shift_event
        )