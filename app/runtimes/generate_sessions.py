"""
Headless data generator: drives several simulated sessions through Kafka into the Bronze layer,
so the Silver/Gold/ML pipelines can be reproduced without driving the cockpit by hand.

    python app/runtimes/generate_sessions.py --sessions 12 --minutes 3
"""
import argparse
import random
import sys
import uuid
from pathlib import Path

# Make the project root importable when the script is run directly
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.app_config import AppConfig  # noqa: E402
from infra.kafka.kafka_client import KafkaService  # noqa: E402
from infra.spark.spark_session import SparkSessionFactory  # noqa: E402
from ml.datasets.feature_config import SIM_DT, TICKS_PER_SEC  # noqa: E402
from pipelines.processor.bronze_processor import BronzeProcessor  # noqa: E402
from simulator.core.loader.car_profile import CarProfileLoader  # noqa: E402
from simulator.core.loader.driver_profile import DriverProfileLoader  # noqa: E402
from simulator.core.loader.environment_profile import EnvironmentLoader  # noqa: E402
from simulator.core.loader.wear_profile import WearProfileLoader  # noqa: E402
from simulator.core.simulation.simulation import Simulation  # noqa: E402
from streaming.events.event_builder import EventBuilder  # noqa: E402
from streaming.kafka.producers.publisher import KafkaEventPublisher  # noqa: E402

# Pedal ranges and how long the driver holds a pedal position, per driving style
STYLES = {
    "eco": {"pedal": (0.10, 0.45), "hold_sec": (6, 15), "brake_prob": 0.10},
    "normal": {"pedal": (0.20, 0.65), "hold_sec": (4, 10), "brake_prob": 0.15},
    "sport": {"pedal": (0.50, 1.00), "hold_sec": (1, 5), "brake_prob": 0.30},
}


def pedal_plan(style: str, ticks: int, rng: random.Random):
    """Yields (pedal, brake) per tick: random segments shaped by the driving style."""
    cfg = STYLES[style]
    tick = 0
    while tick < ticks:
        hold = int(rng.uniform(*cfg["hold_sec"]) * TICKS_PER_SEC)
        braking = rng.random() < cfg["brake_prob"]
        pedal = 0.0 if braking else rng.uniform(*cfg["pedal"])
        brake = rng.uniform(0.3, 0.8) if braking else 0.0
        for _ in range(min(hold, ticks - tick)):
            yield pedal, brake
            tick += 1


def run_session(kafka: KafkaService, car_profile: Path, style: str, minutes: float, rng: random.Random) -> str:
    sim = Simulation(
        CarProfileLoader.load(car_profile),
        DriverProfileLoader.load(AppConfig.MAIN_PROFILES_PATH / "drivers" / f"{style}.yaml"),
        WearProfileLoader.load(AppConfig.WEAR_PROFILE),
        EnvironmentLoader.load(AppConfig.ENVIRONMENT_PROFILE),
    )
    # Seeded session id: the same command always produces the same data and train/test split
    sim.simulation_id = str(uuid.UUID(int=rng.getrandbits(128), version=4))
    EventBuilder(sim.state_bus, KafkaEventPublisher(kafka, AppConfig.TOPIC_SIMULATION_RAW))

    for pedal, brake in pedal_plan(style, int(minutes * 60 * TICKS_PER_SEC), rng):
        sim.driver.set_external_pedal(pedal)
        sim.driver.set_external_brake(brake)
        sim.step(SIM_DT)  # as fast as possible: simulated time, not wall-clock time

    kafka.producer().flush()
    return sim.simulation_id


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sessions", type=int, default=12)
    parser.add_argument("--minutes", type=float, default=3.0, help="simulated minutes per session")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    cars = sorted((AppConfig.MAIN_PROFILES_PATH / "cars").glob("*.yaml"))
    styles = list(STYLES)

    spark = SparkSessionFactory.create("bronze-ingestion-generator")
    query = BronzeProcessor(spark).run()
    kafka = KafkaService(AppConfig.KAFKA_BROKERS)

    try:
        for i in range(args.sessions):
            car, style = cars[i % len(cars)], styles[i % len(styles)]
            sim_id = run_session(kafka, car, style, args.minutes, rng)
            print(f"[{i + 1}/{args.sessions}] {car.stem:<12} {style:<7} -> {sim_id}")

        print("Waiting for Bronze ingestion to catch up...")
        query.processAllAvailable()
    finally:
        query.stop()
        spark.stop()
    print(f"Done. Bronze events are in {AppConfig.lake_root(AppConfig.BRONZE_CONTAINER)}")


if __name__ == "__main__":
    main()
