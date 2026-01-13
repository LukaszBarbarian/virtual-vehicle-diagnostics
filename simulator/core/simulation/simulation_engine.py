# simulator/core/simulation/simulation_engine.py

import threading
import time
from simulator.core.simulation.simulation import Simulation


class SimulationEngine:
    def __init__(self, simulation: Simulation):
        self.simulation = simulation
        self.running = False
        self.thread = None
        self.on_tick = None

    def start_loop(self, dt=0.1):
        if self.running:
            return

        self.running = True

        def loop():
            while self.running:
                if self.on_tick:
                    self.on_tick(dt)
                self.simulation.step(dt)
                time.sleep(dt)

        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()

    def stop_loop(self):
        self.running = False
