# engine.py
from dataclasses import dataclass
from core.base import BaseModule, BaseState, BaseInput, BaseOutput
import math

from core.config_models import EngineConfig

@dataclass
class EngineState(BaseState):
    engine_rpm: float
    engine_temp_c: float
    oil_temp_c: float
    efficiency: float
    rotational_inertia: float
    fuel_rate_lph: float = 0.0
    fuel_l_per_100km: float = 0.0

@dataclass
class EngineInput(BaseInput):
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
    torque_nm: float
    fuel_rate_lph: float
    heat_kw: float
    engine_rpm: float
    fuel_l_per_100km: float

class EngineModule(BaseModule):
    def __init__(self, initial_state: EngineState):
        self.state = initial_state
        self.input = None
        self.output = None

        # z profilu auta
        self.max_rpm = 9000.0
        self.base_torque = 250.0
        self.peak_rpm = 4000.0
        self.max_power_kw = 480.0   # <-- NOWE (Huracan ≈ 480 kW)


    def apply_config(self, cfg: EngineConfig):
        self.max_rpm = cfg.max_rpm
        self.idle_rpm = cfg.idle_rpm
        self.base_torque = cfg.base_torque_nm
        self.peak_rpm = cfg.peak_rpm
        self.max_power_kw = cfg.max_power_kw
        self.state.rotational_inertia = cfg.rotational_inertia
        self.state.efficiency = cfg.efficiency

        self.bsfc = cfg.bsfc
        self.heat_fraction = cfg.heat_fraction

        self.rpm_response = cfg.rpm_response
        self.shift_rpm_drop_rate = cfg.shift_rpm_drop_rate
        self.torque_curve_min = cfg.torque_curve_min
        self.limiter_start_ratio = cfg.limiter_start_ratio
        self.limiter_torque_factor = cfg.limiter_torque_factor

    def _efficiency_map(self, rpm: float, load: float):
        # rpm_ratio: 0..1
        rpm_ratio = rpm / self.max_rpm

        # charakterystyka typowego silnika V10
        # najlepsza sprawność: ~40–70% RPM, średnie obciążenie
        eff_rpm = math.exp(-((rpm_ratio - 0.55) ** 2) / 0.05)
        eff_load = math.exp(-((load - 0.6) ** 2) / 0.08)

        return 0.55 + 0.45 * eff_rpm * eff_load


    def _rpm_from_wheels(self, vehicle_speed_kmh: float, wheel_radius_m: float):
        v_mps = vehicle_speed_kmh / 3.6
        return v_mps / (2.0 * math.pi * max(0.1, wheel_radius_m)) * 60.0

    def update(self, dt: float):
        i: EngineInput = self.input
        s: EngineState = self.state

        idle_rpm = self.idle_rpm
        max_rpm = self.max_rpm

        if i.clutch_factor < 0.5:
            # silnik chwilowo odciążony
            s.engine_rpm += (idle_rpm - s.engine_rpm) * self.shift_rpm_drop_rate * dt
            s.fuel_rate_lph *= 0.3
            s.fuel_l_per_100km *= 0.3
            self.output = EngineOutput(
                torque_nm=0.0,
                fuel_rate_lph=s.fuel_rate_lph,
                fuel_l_per_100km=s.fuel_l_per_100km,
                heat_kw=0.0,
            engine_rpm=s.engine_rpm
            )
            return



        # === RPM z napędu ===
        wheel_rpm = self._rpm_from_wheels(i.vehicle_speed, i.wheel_radius_m)

        if i.current_gear > 0 and i.clutch_factor > 0 and i.vehicle_speed > 0.5:
            target_rpm = wheel_rpm * i.gear_ratio_total
        else:
            target_rpm = idle_rpm + i.throttle * (max_rpm - idle_rpm)

        # bezwładność
        alpha = min(1.0, self.rpm_response * dt)
        s.engine_rpm += (target_rpm - s.engine_rpm) * alpha

        s.engine_rpm = max(idle_rpm, min(max_rpm, s.engine_rpm))

        # === KRZYWA MOMENTU ===
        x = s.engine_rpm / max(1.0, self.peak_rpm)
        torque_curve = max(self.torque_curve_min, 1.0 - (x - 1.0) ** 2)
        load = self.vehicle.state.load if hasattr(self, "vehicle") else 0.5
        map_eff = self._efficiency_map(s.engine_rpm, load)
        effective_eff = map_eff * (1.0 - i.torque_loss_factor)

        combustion_torque = self.base_torque * torque_curve * i.throttle * effective_eff

        # soft limiter
        if s.engine_rpm > max_rpm * self.limiter_start_ratio:
            combustion_torque *= self.limiter_torque_factor


        # === SKALOWANIE MOCY (KLUCZ DO HURACANA) ===
        omega = s.engine_rpm * 2.0 * math.pi / 60.0
        current_power_kw = combustion_torque * omega / 1000.0

        if i.vehicle_speed < 2.0:
            combustion_torque = max(combustion_torque, 0.35 * self.base_torque * i.throttle)

        # 2️⃣ dopiero potem miękki limiter mocy
        excess = max(0.0, current_power_kw - self.max_power_kw)
        soft = 1.0 / (1.0 + excess / self.max_power_kw)
        combustion_torque *= soft

        power_kw = (combustion_torque * s.engine_rpm * 2 * math.pi) / 60000.0
        power_kw = min(power_kw, self.max_power_kw * i.throttle)

        bsfc = self.bsfc
        idle_power_kw = 0.04 * (s.engine_rpm / self.max_rpm) * self.max_power_kw

        effective_power_kw = power_kw + idle_power_kw

        fuel_kg_per_h = effective_power_kw * bsfc
        s.fuel_rate_lph = fuel_kg_per_h / 0.745

        heat_kw = power_kw * 0.65

        if i.vehicle_speed < 10.0:
            s.fuel_l_per_100km = None  # albo 0.0, albo zostaw poprzednią
        else:
            s.fuel_l_per_100km = s.fuel_rate_lph / i.vehicle_speed * 100.0


        self.output = EngineOutput(
            torque_nm=combustion_torque,
            fuel_rate_lph=s.fuel_rate_lph,
            heat_kw=heat_kw,
            engine_rpm=s.engine_rpm,
            fuel_l_per_100km=s.fuel_l_per_100km
        )
