from dataclasses import asdict, dataclass
from typing import Dict, Any

@dataclass
class RawSimulationState:
    """
    Data structure representing a complete snapshot of the simulation state at a specific point in time.
    """
    time: float
    step: int
    simulation_id: str
    modules: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the state object and all its nested module data into a standard dictionary.
        """
        return asdict(self)