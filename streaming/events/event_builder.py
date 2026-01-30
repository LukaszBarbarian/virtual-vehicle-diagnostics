from streaming.events.simulation import RawSimulationStateEvent
from streaming.kafka.producers.base import EventPublisher

class EventBuilder:
    """
    Coordinates the transformation of internal simulation states into publishable stream events.
    """
    def __init__(self, state_bus, publisher: EventPublisher):
        """
        Initializes the builder by connecting to the state bus and setting up the event publisher.
        """
        self.publisher = publisher
        state_bus.subscribe(self.on_state)

    def on_state(self, raw_state):
        """
        Callback triggered on state changes to wrap raw data into a simulation event and publish it.
        """
        event = RawSimulationStateEvent(
            raw_state_dict=raw_state.to_dict()
        )
        self.publisher.publish(event.to_dict())