# runtime/driver_service.py
# runtime/driver_service.py
import threading
from simulator.modules.driver import DriverModule


class DriverService:
    def __init__(self, driver_module: DriverModule):
        self.driver = driver_module

    def handle_driver_command(self, msg: dict):
        throttle = msg.get("pedal")
        brake = msg.get("brake")

        if throttle is not None:
            self.driver.set_external_pedal(max(0.0, min(1.0, throttle)))
        
        if brake is not None:
            # We need to add this method to DriverModule
            self.driver.set_external_brake(max(0.0, min(1.0, brake)))


