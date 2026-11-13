import threading
import time
import traceback

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
        self.on_error = None

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
        next_tick = time.perf_counter()
        while self.running:
            try:
                self.sim.step(dt)
            except Exception:
                # Surface the failure (e.g. Kafka unreachable) instead of silently killing the thread
                traceback.print_exc()
                self.running = False
                if self.on_error:
                    self.on_error()
                break
            # Keep a fixed tick rate regardless of how long the step took
            next_tick += dt
            time.sleep(max(0.0, next_tick - time.perf_counter()))

    def stop_loop(self):
        """
        Signals the execution thread to terminate and waits for it to finish gracefully.
        """
        self.running = False
        if self._thread:
            self._thread.join(timeout=0.2)
            self._thread = None