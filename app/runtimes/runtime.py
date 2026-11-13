from app.app_config import AppConfig
from infra.kafka.kafka_client import KafkaService
from infra.spark.spark_session import SparkSessionFactory
from pipelines.processor.bronze_processor import BronzeProcessor
from simulator.runtime.runtime import SimulationRuntime
from streaming.kafka.consumers.dashboard import DashboardStateHandler
from streaming.kafka.consumers.runner import KafkaConsumerRunner
from streaming.kafka.producers.driver_command import DriverCommandPublisher
from ml.datasets.feature_config import SIM_DT
from ml.datasets.feature_config import SIM_DT

class ApplicationRuntime:
    """
    Main entry point and orchestrator for the entire application.
    Integrates Simulation, Spark Streaming, and Kafka services.
    """
    def __init__(self, kafka_brokers: str = AppConfig.KAFKA_BROKERS):
        """
        Initializes infrastructure services and triggers the background Spark ingestion.
        """
        self.kafka = KafkaService(kafka_brokers)
        self.simulation_runtime = SimulationRuntime(self.kafka)
        self.spark_initialized = False

        self.dashboard_consumer = None
        self.driver_publisher = None
        self.simulation = None
        self.spark_error = None
        self.spark_error = None

        # Immediate Spark initialization to ensure the Bronze pipeline is ready
        self._initialize_spark()

    def _initialize_spark(self):
        """
        Initializes the Spark session and starts the Bronze ingestion stream.
        This process runs globally throughout the application lifecycle.
        """
        if self.spark_initialized:
            return

        try:
            self.spark = SparkSessionFactory.create("bronze-ingestion")
            self.processor = BronzeProcessor(self.spark)
            # Start the non-blocking Spark stream
            self.spark_query = self.processor.run()
            self.spark_initialized = True
        except Exception as e:
            # The cockpit keeps working without Spark; telemetry then only goes to Kafka
            self.spark_error = str(e)
            print(f"Runtime Spark Initialization Error: {e}")

    def start_session(self, on_state_cb=None, car_profile_path=None, driver_profile_path=None, on_error=None):
        """
        Initializes a fresh simulation session.
        Ensures any existing session is shutdown to prevent resource leaks.
        """
        # 1. Graceful shutdown of existing simulation and consumers
        self.stop_session()

        # 2. Bootstrap new simulation environment
        self.simulation = self.simulation_runtime.bootstrap(car_profile_path, driver_profile_path)

        if on_state_cb:
            self.simulation.sim.state_bus.subscribe(on_state_cb)
        if on_error:
            self.simulation.engine.on_error = on_error

        # 3. Setup real-time Dashboard consumer with a unique consumer group
        self.dashboard_handler = DashboardStateHandler()
        self.dashboard_consumer = KafkaConsumerRunner(
            kafka=self.kafka,
            topic=AppConfig.TOPIC_SIMULATION_RAW,
            group_id=f"dashboard_{self.simulation.sim.simulation_id}",
            handler=self.dashboard_handler
        )
        self.dashboard_consumer.start()

        # 4. Initialize external command publisher
        self.driver_publisher = DriverCommandPublisher(self.kafka)

        return self.simulation.sim.simulation_id

    def play(self, dt: float = SIM_DT):
        """
        Starts the physics loop for the active simulation.
        """
        if self.simulation:
            self.simulation.start_engine_loop(dt)

    def stop_session(self):
        """
        Terminates the current simulation session and cleans up Kafka consumers.
        Spark ingestion remains active to continue background processing.
        """
        if self.simulation:
            self.simulation.shutdown()
            self.simulation = None

        if self.dashboard_consumer:
            self.dashboard_consumer.stop()
            self.dashboard_consumer = None