from dataclasses import asdict, dataclass
from typing import Dict, Any

@dataclass
class RawSimulationState:
    time: float
    step: int
    simulation_id: str
    modules: Dict[str, Dict[str, Any]]


    def to_dict(self) -> Dict[str, Any]:
            return asdict(self)