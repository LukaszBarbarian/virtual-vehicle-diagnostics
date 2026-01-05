class SimulationClock:
    def __init__(self):
        self.time = 0.0

    def tick(self, dt):
        self.time += dt
