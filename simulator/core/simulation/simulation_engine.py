import time
from simulator.core.simulation.simulation import Simulation


class SimulationEngine:

    def __init__(self, simulation: Simulation):
        self.simulation = simulation
        self.running = False

    def start(self, dt=0.1):
        self.running = True
        while self.running:
            self.simulation.step(dt)
            time.sleep(dt)
