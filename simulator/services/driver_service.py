# runtime/driver_service.py
import threading
from simulator.modules.driver import DriverModule

class DriverService:
    """
    Service layer responsible for translating external control messages into 
    actions within the DriverModule.
    """
    def __init__(self, driver_module: DriverModule):
        """
        Initializes the service with a reference to the active simulation driver.
        """
        self.driver = driver_module

    def handle_driver_command(self, msg: dict):
        """
        Processes incoming command dictionaries to update throttle and brake targets.
        Values are safely clamped between 0.0 and 1.0.
        """
        throttle = msg.get("pedal")
        brake = msg.get("brake")

        if throttle is not None:
            # Overrides the automated profile with manual pedal input
            self.driver.set_external_pedal(max(0.0, min(1.0, throttle)))
        
        if brake is not None:
            # Updates the braking intent
            self.driver.set_external_brake(max(0.0, min(1.0, brake)))