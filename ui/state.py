from enum import Enum

class SimState(str, Enum):
    OFF = "OFF"
    READY = "READY"
    RUNNING = "RUNNING"
