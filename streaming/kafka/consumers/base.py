from abc import ABC, abstractmethod
from typing import Dict, Any


class EventHandler(ABC):
    @abstractmethod
    def handle(self, event: Dict[str, Any]) -> None:
        pass
