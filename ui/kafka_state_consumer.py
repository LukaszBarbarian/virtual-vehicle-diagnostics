import json
import threading
from kafka import KafkaConsumer


class KafkaStateConsumer:
    """
    Czyta raw.simulation.state z Kafki
    i trzyma ostatni znany stan w pamięci
    """

    def __init__(self, brokers: str):
        self.consumer = KafkaConsumer(
            "simulation.raw",
            bootstrap_servers=brokers,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id="dashboard"
        )

        self._lock = threading.Lock()
        self._latest_state = None
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
        for msg in self.consumer:
            if not self._running:
                break

            event = msg.value
            if event.get("event_type") != "raw.simulation.state":
                continue

            with self._lock:
                self._latest_state = event["payload"]

    def stop(self):
        self._running = False
        try:
            self.consumer.close()
        except Exception:
            pass

    def get_latest_state(self):
        with self._lock:
            return self._latest_state
