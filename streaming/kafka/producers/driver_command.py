# streaming/producers/driver_commands.py
from infra.kafka.kafka_client import KafkaService
from streaming.events.driver import DriverCommandEvent


# streaming/producers/driver_commands.py

class DriverCommandPublisher:
    def __init__(self, kafka: KafkaService):
        self.kafka = kafka
        self.topic = "driver.commands"

    def set_controls(self, throttle: float, brake: float):
        """Sends both throttle and brake values to the simulation."""
        event = DriverCommandEvent(pedal=throttle, brake=brake)
        self.kafka.send(self.topic, event.to_dict())
