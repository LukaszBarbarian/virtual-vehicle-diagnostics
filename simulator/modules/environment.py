from dataclasses import dataclass
from core.base import BaseState

@dataclass
class EnvironmentState(BaseState):
    """
    Represents the atmospheric and geographic conditions surrounding the vehicle.
    """
    ambient_temp_c: float = 15.0
    air_density: float = 1.2
    road_incline_pct: float = 0.0