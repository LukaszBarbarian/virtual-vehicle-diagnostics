import threading
import time

class SimulationEngine:
    def __init__(self, sim):
        self.sim = sim
        self.running = False
        self._thread = None

    def start_loop(self, dt: float):
        """
        Starts the simulation physical engine loop in a separate background thread.
        """
        if self.running:
            return
        
        self.running = True
        self._thread = threading.Thread(
            target=self._run, 
            args=(dt,), 
            daemon=True
        )
        self._thread.start()

    def _run(self, dt):
        """
        Internal execution loop that performs physics steps.
        """
        while self.running:
            self.sim.step(dt)
            time.sleep(dt)

    def stop_loop(self):
        """
        Safely halts the simulation engine execution.
        """
        self.running = False
        if self._thread:
            self._thread.join(timeout=0.2)
            self._thread = None