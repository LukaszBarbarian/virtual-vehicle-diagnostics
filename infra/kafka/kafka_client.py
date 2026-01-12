from kafka import KafkaProducer, KafkaConsumer
import json


class KafkaService:
    def __init__(self, brokers: str):
        self.brokers = brokers
        self._producer = None

    def producer(self):
        if not self._producer:
            self._producer = KafkaProducer(
                bootstrap_servers=self.brokers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                linger_ms=5
            )
        return self._producer

    def send(self, topic: str, payload: dict):
        self.producer().send(topic, payload)

    def consume(self, topic: str, group_id: str):
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self.brokers,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        for msg in consumer:
            yield msg.value
