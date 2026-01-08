from streaming.events.base import BaseEvent


class DriverCommandEvent(BaseEvent):
    def __init__(self, pedal: float):
        super().__init__(
            event_type="driver.command",
            event_version=1,
            payload={
                "pedal": pedal
            }
        )
