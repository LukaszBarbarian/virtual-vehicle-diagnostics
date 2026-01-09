from streaming.kafka.kafka_service import KafkaService
from streaming.producers.base import EventPublisher

class KafkaEventPublisher(EventPublisher):
    def __init__(self, kafka: KafkaService, topic: str):
        self.kafka = kafka
        self.topic = topic

    def publish(self, event: dict) -> None:
        self.kafka.send(self.topic, event)
