from app.app_config import AppConfig
from infra.kafka.kafka_client import KafkaService
from streaming.events.driver import DriverCommandEvent


class DriverCommandPublisher:
    """
    Publishes the cockpit's throttle and brake inputs to the driver command topic.
    """
    def __init__(self, kafka: KafkaService):
        self.kafka = kafka
        self.topic = AppConfig.TOPIC_DRIVER_COMMANDS

    def set_controls(self, throttle: float, brake: float):
        """Sends both throttle and brake values to the simulation."""
        event = DriverCommandEvent(pedal=throttle, brake=brake)
        self.kafka.send(self.topic, event.to_dict())
