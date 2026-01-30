from dataclasses import dataclass
from simulator.modules.engine import EngineModule
from simulator.modules.gearbox import GearboxModule
from simulator.modules.thermals import ThermalModule
from simulator.modules.vehicle import VehicleModule

@dataclass
class Car:
    """
    A container class that aggregates all mechanical and thermal modules into a single vehicle entity.
    """
    engine: EngineModule
    gearbox: GearboxModule
    thermals: ThermalModule
    vehicle: VehicleModule