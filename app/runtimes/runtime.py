import threading
from app.app_config import AppConfig
from infra.kafka.kafka_client import KafkaService
from infra.spark.spark_session import SparkSessionFactory
from pipelines.processor.bronze_processor import BronzeProcessor
from simulator.runtime.runtime import SimulationRuntime
from streaming.kafka.consumers.dashboard import DashboardStateHandler
from streaming.kafka.consumers.runner import KafkaConsumerRunner
from streaming.kafka.producers.driver_command import DriverCommandPublisher


class ApplicationRuntime:
    def __init__(self, kafka_brokers: str):
        self.kafka = KafkaService(kafka_brokers)
        self.simulation_runtime = SimulationRuntime(self.kafka)
        self.spark_initialized = False

        self.dashboard_consumer = None
        self.driver_publisher = None
        
        # Inicjalizujemy Sparka od razu przy starcie aplikacji
        self._initialize_spark()

    def _initialize_spark(self):
        if self.spark_initialized:
            return
        print("Spark: Inicjalizacja stała...")
        try:
            self.spark = SparkSessionFactory.create("bronze-ingestion")
            self.processor = BronzeProcessor(self.spark)
            self.spark_query = self.processor.run() 
            self.spark_initialized = True
            print("Spark: Aktywny.")
        except Exception as e:
            print(f"Spark Error: {e}")

    def start_session(self, on_state_cb=None):
        """
        Prepares a new session and ensures the previous one is fully terminated.
        """
        # 1. STOP PREVIOUS SESSION COMPLETELY
        if self.simulation_runtime:
            self.simulation_runtime.shutdown()

        self.simulation = self.simulation_runtime.bootstrap()
        
        if on_state_cb:
            self.simulation.sim.state_bus.subscribe(on_state_cb)
        
        self.dashboard_handler = DashboardStateHandler()
        self.dashboard_consumer = KafkaConsumerRunner(
            kafka=self.kafka,
            topic=AppConfig.TOPIC_SIMULATION_RAW,
            group_id=f"dashboard_{self.simulation.sim.simulation_id}", # UNIQUE GROUP ID
            handler=self.dashboard_handler
        )
        self.dashboard_consumer.start()
        self.driver_publisher = DriverCommandPublisher(self.kafka)
        
        return self.simulation.sim.simulation_id

    def play(self, dt: float = 0.1):
        if self.simulation:
            self.simulation.start_engine_loop(dt)

    def stop_session(self):
        """Pełne zatrzymanie sesji, ale Spark zostaje."""
        if self.simulation:
            self.simulation.shutdown()
            self.simulation = None
        if self.dashboard_consumer:
            self.dashboard_consumer.stop()