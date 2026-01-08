from dataclasses import dataclass, asdict
from typing import Dict, Any
import time
import uuid


@dataclass
class BaseEvent:
    event_type: str
    event_version: int
    payload: Dict[str, Any]

    event_id: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        self.event_id = self.event_id or str(uuid.uuid4())
        self.timestamp = self.timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
