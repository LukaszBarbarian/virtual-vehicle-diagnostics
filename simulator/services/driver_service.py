# runtime/driver_service.py
# runtime/driver_service.py
import threading
from simulator.modules.driver import DriverModule
from streaming.kafka_service import KafkaService


class DriverService:
    def __init__(self, driver_module: DriverModule):
        self.driver = driver_module

    def handle_driver_command(self, msg: dict):
        pedal = msg.get("pedal")

        if pedal is None:
            return

        pedal = max(0.0, min(1.0, pedal))

        self.driver.set_external_pedal(pedal)





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