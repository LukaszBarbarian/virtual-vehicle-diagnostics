from dataclasses import dataclass, asdict
from typing import Dict, Any
import time
import uuid

@dataclass
class BaseEvent:
    """
    A standard data structure for representing system events with unique IDs and timestamps.
    """
    event_type: str
    event_version: int
    payload: Dict[str, Any]

    event_id: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        """
        Generates a unique identifier and records the current time if not provided during initialization.
        """
        self.event_id = self.event_id or str(uuid.uuid4())
        self.timestamp = self.timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the event instance into a standard dictionary format.
        """
        return asdict(self)