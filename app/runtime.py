import threading
from app.app_config import AppConfig
from infra.kafka.kafka_client import KafkaService
from simulator.core.simulation.scenarios.scenario_runner import ScenarioRunner
from simulator.core.simulation.scenarios.scenario_sequence import ScenarioSequence
from simulator.runtime.runtime import SimulationRuntime
from streaming.kafka.consumers.dashboard import DashboardStateHandler
from streaming.kafka.consumers.runner import KafkaConsumerRunner
from streaming.kafka.producers.driver_command import DriverCommandPublisher


class ApplicationRuntime:
    def __init__(self, kafka_brokers: str):
        self.kafka = KafkaService(kafka_brokers)

        self.simulation: SimulationRuntime | None = None
        self.dashboard_consumer = None
        self.dashboard_handler = None
        self.driver_publisher = None

        self.scenario_runner = None
        self.active_scenario_name = None

    # ===============================
    # INIT (NO TIME FLOW)
    # ===============================
    def start(self):
        self.simulation = SimulationRuntime(self.kafka).bootstrap()

        self.dashboard_handler = DashboardStateHandler()
        self.dashboard_consumer = KafkaConsumerRunner(
            kafka=self.kafka,
            topic=AppConfig.TOPIC_SIMULATION_RAW,
            group_id="dashboard",
            handler=self.dashboard_handler
        )
        self.dashboard_consumer.start()

        self.driver_publisher = DriverCommandPublisher(self.kafka)
        return self

    # ===============================
    # ENGINE
    # ===============================
    def start_engine(self):
        """
        Podłącza wszystko.
        NIE uruchamia czasu.
        """
        if not self.simulation:
            raise RuntimeError("Runtime not started")

        # nic więcej – engine jest GOTOWY

    def play(self, dt: float = 0.1):
        """
        JEDYNE miejsce startu czasu.
        """
        if self.simulation:
            self.simulation.start_engine_loop(dt)

    def pause(self):
        if self.simulation:
            self.simulation.stop_engine_loop()

    # ===============================
    # SCENARIOS
    # ===============================
    def start_scenario_sequence(self, scenarios):
        if not self.simulation or not self.driver_publisher:
            raise RuntimeError("Simulation not initialized")

        sequence = ScenarioSequence(scenarios)

        self.scenario_runner = ScenarioRunner(
            scenario_sequence=sequence,
            simulation_runtime=self.simulation,
            driver_publisher=self.driver_publisher
        )

        self.simulation.engine.on_tick = self.scenario_runner.step
        self.active_scenario_name = sequence.name

        # 🔥 scenario AUTOMATYCZNIE uruchamia czas
        self.play()

    def stop_scenario(self):
        if self.simulation and self.simulation.engine:
            self.simulation.engine.on_tick = None

        self.pause()
        self.scenario_runner = None
        self.active_scenario_name = None

    # ===============================
    # FULL STOP
    # ===============================
    def stop(self):
        self.stop_scenario()

        if self.simulation:
            self.simulation.shutdown()

        if self.dashboard_consumer:
            self.dashboard_consumer.stop()

        self.simulation = None
        self.dashboard_consumer = None
        self.dashboard_handler = None
        self.driver_publisher = None
