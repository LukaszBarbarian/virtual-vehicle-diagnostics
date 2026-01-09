from streaming.kafka.kafka_service import KafkaService
from simulator.runtime import SimulationRuntime
from streaming.consumers.runner import KafkaConsumerRunner
from streaming.consumers.dashboard import DashboardStateHandler
from streaming.producers.driver_command import DriverCommandPublisher


class ApplicationRuntime:
    def __init__(self, kafka_brokers: str):
        self.kafka = KafkaService(kafka_brokers)

        self.simulation: SimulationRuntime | None = None
        self.dashboard_consumer: KafkaConsumerRunner | None = None
        self.dashboard_handler: DashboardStateHandler | None = None
        self.driver_publisher: DriverCommandPublisher | None = None

    # ===============================
    # START
    # ===============================
    def start(self):
        # --- SIMULATION ---
        self.simulation = SimulationRuntime(kafka=self.kafka).bootstrap()

        # --- DASHBOARD CONSUMER ---
        self.dashboard_handler = DashboardStateHandler()
        self.dashboard_consumer = KafkaConsumerRunner(
            kafka=self.kafka,
            topic="simulation.raw",
            group_id="dashboard",
            handler=self.dashboard_handler
        )
        self.dashboard_consumer.start()

        # --- DRIVER COMMANDS ---
        self.driver_publisher = DriverCommandPublisher(self.kafka)

        return self

    # ===============================
    # ENGINE CONTROL
    # ===============================
    def start_engine(self, dt: float = 0.1):
        if self.simulation:
            self.simulation.start_engine(dt)

    # ===============================
    # STOP
    # ===============================
    def stop(self):
        if self.simulation:
            self.simulation.shutdown()

        if self.dashboard_consumer:
            self.dashboard_consumer.stop()

        self.simulation = None
        self.dashboard_consumer = None
        self.dashboard_handler = None
        self.driver_publisher = None
