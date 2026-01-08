# streaming/consumers/driver_listener.py
import threading


class DriverKafkaListener:
    def __init__(self, kafka, driver_service):
        self.kafka = kafka
        self.driver_service = driver_service

        self.topic = "driver.commands"
        self.group_id = "driver"

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

            if event.get("event_type") != "driver.command":
                continue

            self.driver_service.handle_driver_command(
                event.get("payload", {})
            )

    def stop(self):
        self._running = False
