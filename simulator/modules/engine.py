# engine.py
from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
import math

from simulator.core.models.model_specification import EngineSpecification

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
    wheel_force_n: float   # ⬅️ KLUCZOWE
    fuel_rate_lph: float
    heat_kw: float
    engine_rpm: float
    fuel_l_per_100km: float


class EngineModule(BaseModule):
    def __init__(self, initial_state: EngineState):
        self.state = initial_state
        self.input = None
        self.output = None

        # wartości domyślne (ustawiane w apply_config)
        self.max_rpm = 9000.0
        self.base_torque = 250.0
        self.peak_rpm = 4000.0
        self.max_power_kw = 480.0

    def apply_config(self, cfg: EngineSpecification):
        self.max_rpm = cfg.max_rpm
        self.idle_rpm = cfg.idle_rpm
        self.base_torque = cfg.base_torque_nm
        self.peak_rpm = 7500

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
        rpm_ratio = rpm / self.max_rpm
        eff_rpm = math.exp(-((rpm_ratio - 0.55) ** 2) / 0.05)
        eff_load = math.exp(-((load - 0.6) ** 2) / 0.08)
        # sprawność zależy od obrotów i obciążenia
        return 0.55 + 0.45 * eff_rpm * eff_load

    def _rpm_from_wheels(self, vehicle_speed_kmh: float, wheel_radius_m: float):
        v_mps = vehicle_speed_kmh / 3.6
        return v_mps / (2.0 * math.pi * max(0.1, wheel_radius_m)) * 60.0

    def update(self, dt: float):
        i: EngineInput = self.input
        s: EngineState = self.state

        idle_rpm = self.idle_rpm
        max_rpm = self.max_rpm

        # =========================
        # SPRZĘGŁO ROZŁĄCZONE
        # =========================
        if i.clutch_factor < 0.5:
            decay = self.shift_rpm_drop_rate * dt
            s.engine_rpm *= max(0.0, 1.0 - decay)

            if s.engine_rpm < idle_rpm:
                s.engine_rpm = idle_rpm

            self.output = EngineOutput(
                torque_nm=0.0,
                wheel_force_n=0.0,
                fuel_rate_lph=s.fuel_rate_lph * 0.4,
                heat_kw=0.0,
                engine_rpm=s.engine_rpm,
                fuel_l_per_100km=s.fuel_l_per_100km
            )
            return

        # =========================
        # RPM Z KÓŁ
        # =========================
        wheel_rpm = self._rpm_from_wheels(i.vehicle_speed, i.wheel_radius_m)
        wheel_target_rpm = (
            wheel_rpm * i.gear_ratio_total if i.current_gear > 0 else idle_rpm
        )

        target_rpm = max(idle_rpm, wheel_target_rpm)

        alpha = min(1.0, self.rpm_response * dt)
        delta = target_rpm - s.engine_rpm
        max_delta = 3000.0 * dt
        delta = max(-max_delta, min(max_delta, delta))
        s.engine_rpm += delta * alpha

        # =========================
        # KRZYWA MOMENTU
        # =========================
        x = s.engine_rpm / max(1.0, self.peak_rpm)
        torque_curve = max(self.torque_curve_min, 1.0 - (x - 1.0) ** 2)

        load = self.vehicle.state.load if hasattr(self, "vehicle") else 0.5
        map_eff = self._efficiency_map(s.engine_rpm, load)
        effective_eff = map_eff * (1.0 - i.torque_loss_factor)

        # =========================
        # OGRANICZENIE MOCĄ (GAZ)
        # =========================
        available_power_kw = self.max_power_kw * i.throttle
        omega = max(1e-3, s.engine_rpm * 2.0 * math.pi / 60.0)
        power_limited_torque = (available_power_kw * 1000.0) / omega

        raw_engine_torque = min(
            self.base_torque * torque_curve,
            power_limited_torque
        ) * effective_eff

        # =========================
        # 🔑 TŁUMIENIE MOMENTU (KLUCZ)
        # =========================
        if not hasattr(s, "engine_torque_filtered"):
            s.engine_torque_filtered = raw_engine_torque

        s.engine_torque_filtered += (
            raw_engine_torque - s.engine_torque_filtered
        ) * 0.15

        engine_torque = s.engine_torque_filtered

        # limiter obrotów
        if s.engine_rpm > max_rpm * self.limiter_start_ratio:
            engine_torque *= self.limiter_torque_factor

        drive_torque = engine_torque * i.gear_ratio_total * i.clutch_factor
        wheel_force = drive_torque / max(0.1, i.wheel_radius_m)

        power_kw = engine_torque * omega / 1000.0

        # =========================
        # SPALANIE (BSFC)
        # =========================
        bsfc = self.bsfc
        fuel_kg_per_h = power_kw * bsfc / max(0.3, map_eff)

        idle_power_kw = 0.02 * self.max_power_kw
        fuel_kg_per_h += idle_power_kw * bsfc

        s.fuel_rate_lph = fuel_kg_per_h / 0.745

        if i.vehicle_speed < 10.0:
            s.fuel_l_per_100km = None
        else:
            s.fuel_l_per_100km = s.fuel_rate_lph / i.vehicle_speed * 100.0

        self.output = EngineOutput(
            torque_nm=engine_torque,
            wheel_force_n=wheel_force,
            fuel_rate_lph=s.fuel_rate_lph,
            heat_kw=power_kw * 0.65,
            engine_rpm=s.engine_rpm,
            fuel_l_per_100km=s.fuel_l_per_100km
        )
