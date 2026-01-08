# streaming/producers/driver_commands.py
from streaming.kafka_service import KafkaService
from streaming.events.driver import DriverCommandEvent


class DriverCommandPublisher:
    def __init__(self, kafka: KafkaService):
        self.kafka = kafka
        self.topic = "driver.commands"

    def set_throttle(self, value: float):
        event = DriverCommandEvent(pedal=value)
        self.kafka.send(self.topic, event.to_dict())
