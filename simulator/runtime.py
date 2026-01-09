# simulator/bootstrap/runtime.py
import threading

from simulator.core.loader.car_profile import CarProfileLoader
from simulator.core.loader.driver_profile import DriverProfileLoader
from simulator.core.loader.environment_profile import EnvironmentLoader
from simulator.core.loader.wear_profile import WearProfileLoader
from simulator.core.simulation.simulation import Simulation
from simulator.core.simulation.simulation_engine import SimulationEngine

from simulator.services.driver_service import DriverService
from streaming.consumers.driver_listener import DriverKafkaListener
from streaming.events.event_builder import EventBuilder
from streaming.kafka.kafka_service import KafkaService
from streaming.producers.kafka import KafkaEventPublisher


MAIN_PROFILES_PATH = "simulator/profiles"


class SimulationRuntime:
    """
    Runtime = orkiestrator cyklu życia symulacji.
    NIE jest symulatorem, NIE jest UI.
    """

    def __init__(self, kafka: KafkaService):
        self.sim: Simulation | None = None
        self.engine: SimulationEngine | None = None
        self.driver_listener: DriverKafkaListener | None = None

        self._engine_thread: threading.Thread | None = None
        self._bootstrapped = False
        self._running = False

        self._kafka: KafkaService = kafka
        self.car_spec = None
        self.driver_spec = None
        self.wear_spec = None
        self.env_spec = None

    # =====================================================
    # BOOTSTRAP (NO ENGINE START)
    # =====================================================
    def bootstrap(self):
        if self._bootstrapped:
            return self

        # --- LOAD PROFILES ---
        car_spec = CarProfileLoader.load(
            f"{MAIN_PROFILES_PATH}/cars/ford_focus.yaml"
        )
        driver_spec = DriverProfileLoader.load(
            f"{MAIN_PROFILES_PATH}/drivers/normal.yaml"
        )
        wear_spec = WearProfileLoader.load(
            f"{MAIN_PROFILES_PATH}/worlds/realistic_wear.yaml"
        )
        env_spec = EnvironmentLoader.load(
            f"{MAIN_PROFILES_PATH}/worlds/summer.yaml"
        )

        self.car_spec = car_spec
        self.driver_spec = driver_spec
        self.wear_spec = wear_spec
        self.env_spec = env_spec

        # --- SIMULATION CORE ---
        self.sim = Simulation(
            car_spec,
            driver_spec,
            wear_spec,
            env_spec
        )

        
        # --- STATE → EVENTS (Kafka OUT) ---
        publisher = KafkaEventPublisher(
            kafka=self._kafka,
            topic="simulation.raw"
        )
        EventBuilder(self.sim.state_bus, publisher)

        # --- DRIVER CONTROL (Kafka IN) ---
        driver_service = DriverService(self.sim.driver)
        self.driver_listener = DriverKafkaListener(
            kafka=self._kafka,
            driver_service=driver_service
        )
        self.driver_listener.start()

        # --- ENGINE (NOT RUNNING YET) ---
        self.engine = SimulationEngine(self.sim)

        self._bootstrapped = True
        return self

    # =====================================================
    # ENGINE CONTROL
    # =====================================================
    def start_engine(self, dt: float = 0.1):
        if self._running:
            return

        if not self._bootstrapped or not self.engine:
            raise RuntimeError("SimulationRuntime not bootstrapped")

        self._running = True
        self.engine.running = True

        self._engine_thread = threading.Thread(
            target=self.engine.start,
            args=(dt,),
            daemon=True
        )
        self._engine_thread.start()

    def stop_engine(self):
        if not self._running:
            return

        self._running = False

        if self.engine:
            self.engine.running = False

        if self._engine_thread:
            self._engine_thread.join(timeout=1.0)
            self._engine_thread = None

    # =====================================================
    # FULL SHUTDOWN (IMPORTANT)
    # =====================================================
    def shutdown(self):
        """
        Całkowite zatrzymanie runtime (STOP + cleanup).
        Wywoływać przy STOP w UI.
        """
        self.stop_engine()

        if self.driver_listener:
            self.driver_listener.stop()
            self.driver_listener = None

        self.sim = None
        self.engine = None
        self._bootstrapped = False
