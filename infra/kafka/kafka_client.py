from kafka import KafkaProducer, KafkaConsumer
import json

class KafkaService:
    """
    Core messaging service for Kafka integration. 
    Handles lazy-loaded producer connections and streaming consumers.
    """
    def __init__(self, brokers: str):
        """
        Initializes the service with the target Kafka broker addresses.
        """
        self.brokers = brokers
        self._producer = None

    def producer(self) -> KafkaProducer:
        """
        Provides a singleton-like KafkaProducer instance. 
        Serializes dictionary payloads into UTF-8 encoded JSON strings.
        """
        if not self._producer:
            self._producer = KafkaProducer(
                bootstrap_servers=self.brokers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                linger_ms=5 # Optimized for small, frequent simulation updates
            )
        return self._producer

    def send(self, topic: str, payload: dict):
        """
        Asynchronously pushes a message to the specified Kafka topic.
        """
        self.producer().send(topic, payload)

    def consume(self, topic: str, group_id: str):
        """
        Creates a blocking generator to consume messages from a specific topic.
        Resets to the latest offset by default to prioritize real-time data.
        """
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