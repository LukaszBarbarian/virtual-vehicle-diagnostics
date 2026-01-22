import sys
from pathlib import Path

from infra.spark.spark_session import SparkSessionFactory
from pipelines.processor.bronze_processor import BronzeProcessor
from pipelines.processor.gold_processor import GoldProcessor
from pipelines.processor.silver_processor import SilverProcessor

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

def run_all(spark):
    print(f"\n🚀 Running BronzeProcessor")
    BronzeProcessor(spark).run()

    print(f"\n🚀 Running SilverProcessor")
    SilverProcessor(spark).run()

    print(f"\n🚀 Running GoldProcessor")
    GoldProcessor(spark).run()
    

if __name__ == "__main__":
    spark = SparkSessionFactory.create("pipelines-process")
    run_all(spark)


    print("\n✅ PIPELINES (Bronze → Gold) FINISHED")
