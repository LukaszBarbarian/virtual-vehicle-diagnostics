from abc import ABC, abstractmethod
from typing import Dict, Any

class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event: Dict[str, Any]) -> None:
        pass
