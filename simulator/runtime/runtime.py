# simulator/runtime/runtime.py

from app.app_config import AppConfig
from infra.kafka.kafka_client import KafkaService
from simulator.core.loader.car_profile import CarProfileLoader
from simulator.core.loader.driver_profile import DriverProfileLoader
from simulator.core.loader.environment_profile import EnvironmentLoader
from simulator.core.loader.wear_profile import WearProfileLoader
from simulator.core.simulation.simulation import Simulation
from simulator.core.simulation.simulation_engine import SimulationEngine
from simulator.services.driver_service import DriverService
from streaming.events.event_builder import EventBuilder
from streaming.kafka.consumers.driver_listener import DriverKafkaListener
from streaming.kafka.producers.publisher import KafkaEventPublisher


class SimulationRuntime:
    """
    Runtime = bootstrap + lifecycle.
    NIE posiada loopa.
    """

    def __init__(self, kafka: KafkaService):
        self.sim: Simulation | None = None
        self.engine: SimulationEngine | None = None
        self.driver_listener: DriverKafkaListener | None = None

        self._kafka = kafka
        self._bootstrapped = False

    # =====================================================
    # BOOTSTRAP (NO TIME FLOW)
    # =====================================================
    def bootstrap(self):
        if self._bootstrapped:
            return self

        car_spec = CarProfileLoader.load(
            f"{AppConfig.MAIN_PROFILES_PATH}/cars/ford_focus.yaml"
        )
        driver_spec = DriverProfileLoader.load(
            f"{AppConfig.MAIN_PROFILES_PATH}/drivers/normal.yaml"
        )
        wear_spec = WearProfileLoader.load(
            f"{AppConfig.MAIN_PROFILES_PATH}/worlds/realistic_wear.yaml"
        )
        env_spec = EnvironmentLoader.load(
            f"{AppConfig.MAIN_PROFILES_PATH}/worlds/summer.yaml"
        )

        self.car_spec = car_spec
        self.driver_spec = driver_spec
        self.wear_spec = wear_spec
        self.env_spec = env_spec

        self.sim = Simulation(
            car_spec,
            driver_spec,
            wear_spec,
            env_spec
        )

        # --- STATE → EVENTS ---
        publisher = KafkaEventPublisher(
            kafka=self._kafka,
            topic=AppConfig.TOPIC_SIMULATION_RAW
        )
        EventBuilder(self.sim.state_bus, publisher)

        # --- DRIVER INPUT ---
        driver_service = DriverService(self.sim.driver)
        self.driver_listener = DriverKafkaListener(
            kafka=self._kafka,
            driver_service=driver_service
        )
        self.driver_listener.start()

        # --- ENGINE (STOPPED) ---
        self.engine = SimulationEngine(self.sim)

        self._bootstrapped = True
        return self

    # =====================================================
    # ENGINE CONTROL (DELEGATION ONLY)
    # =====================================================
    def start_engine_loop(self, dt: float = 0.1):
        if not self.engine:
            raise RuntimeError("Engine not initialized")
        self.engine.start_loop(dt)

    def stop_engine_loop(self):
        if self.engine:
            self.engine.stop_loop()

    # =====================================================
    # SHUTDOWN
    # =====================================================
    def shutdown(self):
        self.stop_engine_loop()

        if self.driver_listener:
            self.driver_listener.stop()
            self.driver_listener = None

        self.sim = None
        self.engine = None
        self._bootstrapped = False
