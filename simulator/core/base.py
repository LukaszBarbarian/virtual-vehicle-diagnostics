from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class BaseState:
    pass

@dataclass
class BaseInput:
    pass

@dataclass
class BaseOutput:
    pass


class BaseModule(ABC):
    def __init__(self):
        self.state = None

    @abstractmethod
    def update(self, dt: float):
        pass


    @abstractmethod
    def apply_config(self, config):
        pass