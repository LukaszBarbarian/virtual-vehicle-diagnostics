class SimulationContext:
    def __init__(self):
        self.time = 0.0
        self.step = 0
        self.vehicle_state = None
        self.engine_state = None
        self.wear_state = None
        self.telemetry = []
