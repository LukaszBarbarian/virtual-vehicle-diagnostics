from dataclasses import dataclass
from simulator.core.base import BaseModule, BaseState, BaseInput, BaseOutput
from simulator.core.models.model_specification import ThermalSpecification

@dataclass
class ThermalState(BaseState):
    coolant_temp_c: float
    oil_temp_c: float
    fan_active: bool
    thermal_mass: float


@dataclass
class ThermalInput(BaseInput):
    heat_kw: float
    vehicle_speed: float
    ambient_temp_c: float
    cooling_efficiency: float

@dataclass
class ThermalOutput(BaseOutput):
    coolant_temp_c: float
    oil_temp_c: float
    fan_active: bool

class ThermalModule(BaseModule):
    def __init__(self, initial_state: ThermalState):
        self.state = initial_state
        self.input = None
        self.output = None

    def apply_config(self, cfg: ThermalSpecification):
        self.thermostat_open_temp = cfg.thermostat_open_temp
        self.fan_on_temp = cfg.fan_on_temp
        self.fan_off_temp = cfg.fan_off_temp

        self.airflow_coeff = cfg.airflow_coeff
        self.cooling_coeff = cfg.cooling_coeff
        self.heat_to_coolant_ratio = cfg.heat_to_coolant_ratio
        self.oil_response_rate = cfg.oil_response_rate


    def update(self, dt: float):
        i = self.input
        s = self.state

        ambient = i.ambient_temp_c

        # === Termostat ===
        thermostat_open = s.coolant_temp_c > self.thermostat_open_temp

        # === Strumienie energii ===
        heat_in = i.heat_kw * self.heat_to_coolant_ratio

        airflow = self.airflow_coeff * i.vehicle_speed
        if thermostat_open:
            cooling = airflow * i.cooling_efficiency * (s.coolant_temp_c - ambient) * self.cooling_coeff
        else:
            cooling = 0.3

        # === Bilans cieplny chłodziwa ===
        net_heat = heat_in - cooling

        # integracja temperatury (to był brakujący element!)
        s.coolant_temp_c += (net_heat * dt) / max(1.0, s.thermal_mass)

        # === Olej reaguje wolniej ===
        s.oil_temp_c += (s.coolant_temp_c - s.oil_temp_c) * self.oil_response_rate * dt

        # === Wentylator ===
        if s.coolant_temp_c > self.fan_on_temp:
            s.fan_active = True
        elif s.coolant_temp_c < self.fan_off_temp:
            s.fan_active = False

        self.output = ThermalOutput(
            coolant_temp_c=s.coolant_temp_c,
            oil_temp_c=s.oil_temp_c,
            fan_active=s.fan_active
        )
