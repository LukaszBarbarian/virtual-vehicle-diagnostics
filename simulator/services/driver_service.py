# runtime/driver_service.py
# runtime/driver_service.py
import threading
from simulator.modules.driver import DriverModule


class DriverService:
    def __init__(self, driver_module: DriverModule):
        self.driver = driver_module

    def handle_driver_command(self, msg: dict):
        pedal = msg.get("pedal")

        if pedal is None:
            return

        pedal = max(0.0, min(1.0, pedal))

        self.driver.set_external_pedal(pedal)





