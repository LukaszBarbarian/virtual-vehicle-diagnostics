from streaming.kafka_service import KafkaService


class KafkaCollector:
    def __init__(self, kafka: KafkaService):
        self.kafka = kafka

    def handle(self, event: dict):
        topic = event["type"]
        self.kafka.send(topic, event)
