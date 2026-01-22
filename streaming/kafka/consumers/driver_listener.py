# streaming/consumers/driver_listener.py
import threading

from infra.kafka.kafka_client import KafkaService
from simulator.services.driver_service import DriverService


class DriverKafkaListener:
    def __init__(self, kafka: KafkaService, driver_service: DriverService, simulation_id: str):
        self.kafka = kafka
        self.driver_service = driver_service
        self.topic = "driver.commands"
        # UNIQUE group_id prevents reading old messages from previous sessions
        self.group_id = f"driver_{simulation_id}" 
        
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
