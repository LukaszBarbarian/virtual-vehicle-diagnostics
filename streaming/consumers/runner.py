import threading
from streaming.kafka.kafka_service import KafkaService
from streaming.consumers.base import EventHandler


class KafkaConsumerRunner:
    def __init__(
        self,
        kafka: KafkaService,
        topic: str,
        group_id: str,
        handler: EventHandler,
    ):
        self.kafka = kafka
        self.topic = topic
        self.group_id = group_id
        self.handler = handler

        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            daemon=True
        )
        self._thread.start()

    def _run(self):
        for event in self.kafka.consume(self.topic, self.group_id):
            if not self._running:
                break
            self.handler.handle(event)

    def stop(self):
        self._running = False
