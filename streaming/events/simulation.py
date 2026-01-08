from streaming.events.base import BaseEvent


class RawSimulationStateEvent(BaseEvent):
    def __init__(self, raw_state_dict: dict):
        super().__init__(
            event_type="simulation.raw",
            event_version=1,
            payload=raw_state_dict
        )
