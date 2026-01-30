from streaming.events.base import BaseEvent

class DriverCommandEvent(BaseEvent):
    """
    Represents a specific event containing driver input commands for throttle and brake levels.
    """
    def __init__(self, pedal: float, brake: float):
        """
        Initializes the event with the driver's pedal positions and sets the event metadata.
        """
        super().__init__(
            event_type="driver.command",
            event_version=1,
            payload={
                "pedal": pedal,
                "brake": brake
            }
        )