# runtime/driver_service.py
# runtime/driver_service.py
import threading
from streaming.kafka_service import KafkaService


class DriverService:
    def __init__(self, driver_module):
        self.driver = driver_module

    def handle_driver_command(self, msg: dict):
        throttle = msg.get("throttle", 0.0)

        # clamp
        throttle = max(0.0, min(1.0, throttle))

        self.driver.cruise_throttle = throttle




class DriverKafkaListener(threading.Thread):
    def __init__(self, kafka: KafkaService, driver_service: DriverService):
        super().__init__(daemon=True)
        self.kafka = kafka
        self.driver_service = driver_service

    def run(self):
        for msg in self.kafka.consume(
            topic="driver.commands",
            group_id="driver-runtime"
        ):
            self.driver_service.handle_driver_command(msg)