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
    """
    Simulates engine thermal dynamics, including heat transfer between 
    coolant, oil, and ambient air.
    """
    def __init__(self, initial_state: ThermalState):
        self.state = initial_state
        self.input = None
        self.output = ThermalOutput(
            coolant_temp_c=initial_state.coolant_temp_c,
            oil_temp_c=initial_state.oil_temp_c,
            fan_active=False
        )

    def apply_config(self, cfg: ThermalSpecification):
        self.spec = cfg
        # Mapping config to internal variables
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

        v_mps = i.vehicle_speed / 3.6
        
        # 1. Airflow logic
        ram_air = v_mps * self.airflow_coeff
        
        # Fan control logic
        if s.coolant_temp_c > self.fan_on_temp:
            s.fan_active = True
        elif s.coolant_temp_c < self.fan_off_temp:
            s.fan_active = False
            
        fan_air = 5.0 if s.fan_active else 0.0
        total_airflow = (ram_air + fan_air) * i.cooling_efficiency

        # 2. Coolant Heat Balance
        heat_in = i.heat_kw * self.heat_to_coolant_ratio
        
        # Cooling efficiency increases when thermostat is open
        thermostat_factor = 1.0 if s.coolant_temp_c > self.thermostat_open_temp else 0.1
        cooling_power = total_airflow * (s.coolant_temp_c - i.ambient_temp_c) * self.cooling_coeff * 50.0
        
        net_coolant_heat = heat_in - (cooling_power * thermostat_factor)
        
        # Temperature integration
        s.coolant_temp_c += (net_coolant_heat * dt) / s.thermal_mass
        
        # 3. Oil Temperature (follows coolant with delay and friction heat)
        # Oil is usually 10-20 degrees hotter than coolant under load
        target_oil_temp = s.coolant_temp_c + (i.heat_kw * 0.5)
        s.oil_temp_c += (target_oil_temp - s.oil_temp_c) * self.oil_response_rate * dt

        self.output = ThermalOutput(
            coolant_temp_c=s.coolant_temp_c,
            oil_temp_c=s.oil_temp_c,
            fan_active=s.fan_active
        )