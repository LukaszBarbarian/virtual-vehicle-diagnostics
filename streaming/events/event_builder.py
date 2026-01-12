# streaming/event_builder.py
from streaming.events.simulation import RawSimulationStateEvent
from streaming.kafka.producers.base import EventPublisher


class EventBuilder:
    def __init__(self, state_bus, publisher: EventPublisher):
        self.publisher = publisher
        state_bus.subscribe(self.on_state)

    def on_state(self, raw_state):
        event = RawSimulationStateEvent(
            raw_state_dict=raw_state.to_dict()
        )
        self.publisher.publish(event.to_dict())
