from simulator.core.state.raw_state import RawSimulationState
from simulator.core.state.state_bus import StateBus
from streaming.kafka_collector import KafkaCollector


class EventBuilder:
    def __init__(self, state_bus: StateBus, collector: KafkaCollector):
        state_bus.subscribe(self.on_state)
        self.collector = collector

    def on_state(self, raw_state: RawSimulationState):
        event = {
            "type": "raw.simulation.state",
            "timestamp": raw_state.time,
            "data": raw_state.to_dict()
        }
        self.collector.handle(event)
