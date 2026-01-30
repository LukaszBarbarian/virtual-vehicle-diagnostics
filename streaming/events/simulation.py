from streaming.events.base import BaseEvent

class RawSimulationStateEvent(BaseEvent):
    """
    An event container designed to encapsulate the complete raw state of the simulation for streaming.
    """
    def __init__(self, raw_state_dict: dict):
        """
        Wraps the provided simulation state dictionary into a versioned event payload.
        """
        super().__init__(
            event_type="simulation.raw",
            event_version=1,
            payload=raw_state_dict
        )