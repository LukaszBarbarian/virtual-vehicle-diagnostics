import threading
import time

class SimulationEngine:
    """
    Manages the background execution thread for the simulation's physical calculations.
    """
    def __init__(self, sim):
        """
        Initializes the engine with a reference to the simulation core.
        """
        self.sim = sim
        self.running = False
        self._thread = None

    def start_loop(self, dt: float):
        """
        Launches the simulation loop in a dedicated background thread to maintain real-time performance.
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
        The internal loop that triggers physics steps at defined intervals until stopped.
        """
        while self.running:
            self.sim.step(dt)
            time.sleep(dt)

    def stop_loop(self):
        """
        Signals the execution thread to terminate and waits for it to finish gracefully.
        """
        self.running = False
        if self._thread:
            self._thread.join(timeout=0.2)
            self._thread = None