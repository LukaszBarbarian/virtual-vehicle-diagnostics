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
    Manages the bootstrapping and lifecycle of the simulation environment.
    Responsible for orchestrating modules, loading profiles, and handling Kafka connectivity.
    """

    def __init__(self, kafka: KafkaService):
        """
        Initializes the runtime with Kafka infrastructure and state accumulators.
        """
        self.sim: Simulation | None = None
        self.engine: SimulationEngine | None = None
        self.driver_listener: DriverKafkaListener | None = None

        self._kafka = kafka
        self._bootstrapped = False
        self.current_wear_accumulator = 0.0

    def bootstrap(self):
        """
        Loads configuration profiles and initializes the simulation engine and event publishers.
        Ensures the environment is ready for execution without starting the time flow.
        """
        if self._bootstrapped:
            return self

        # Load specifications from YAML profiles
        car_spec = CarProfileLoader.load(f"{AppConfig.MAIN_PROFILES_PATH}/cars/ford_focus.yaml")
        driver_spec = DriverProfileLoader.load(f"{AppConfig.MAIN_PROFILES_PATH}/drivers/normal.yaml")
        wear_spec = WearProfileLoader.load(f"{AppConfig.MAIN_PROFILES_PATH}/worlds/realistic_wear.yaml")
        env_spec = EnvironmentLoader.load(f"{AppConfig.MAIN_PROFILES_PATH}/worlds/summer.yaml")

        self.car_spec = car_spec
        self.driver_spec = driver_spec
        self.wear_spec = wear_spec
        self.env_spec = env_spec

        # Initialize core simulation with loaded specs
        self.sim = Simulation(car_spec, driver_spec, wear_spec, env_spec)

        # Restore accumulated wear state if persisting between sessions
        if self.current_wear_accumulator > 0:
            self.sim.wear.state.engine_wear = self.current_wear_accumulator

        # Setup State → Kafka event pipeline
        publisher = KafkaEventPublisher(
            kafka=self._kafka,
            topic=AppConfig.TOPIC_SIMULATION_RAW
        )
        EventBuilder(self.sim.state_bus, publisher)

        # Initialize Driver Input listener for real-time control (UI/External signals)
        driver_service = DriverService(self.sim.driver)
        self.driver_listener = DriverKafkaListener(
            kafka=self._kafka,
            driver_service=driver_service,
            simulation_id=self.sim.simulation_id
        )
        self.driver_listener.start()

        # Initialize the high-frequency simulation engine
        self.engine = SimulationEngine(self.sim)

        self._bootstrapped = True
        return self

    def start_engine_loop(self, dt: float = 0.1):
        """
        Starts the periodic execution of the simulation physics loop.
        """
        if not self.engine:
            raise RuntimeError("Engine not initialized. Call bootstrap() first.")
        self.engine.start_loop(dt)

    def stop_engine_loop(self):
        """
        Pauses the simulation physics loop.
        """
        if self.engine:
            self.engine.stop_loop()

    def shutdown(self):
        """
        Gracefully shuts down the runtime, persists wear state, and cleans up Kafka listeners.
        """
        self.stop_engine_loop()

        if self.sim:
            # Persist mechanical health state before destroying simulation objects
            self.current_wear_accumulator = self.sim.wear.state.engine_wear
            self.sim.state_bus.clear_subscribers()

        if self.driver_listener:
            self.driver_listener.stop()
            self.driver_listener = None

        self.sim = None
        self.engine = None
        self._bootstrapped = False