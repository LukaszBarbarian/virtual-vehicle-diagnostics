import subprocess
import sys
from pathlib import Path

from infra.spark.spark_session import SparkSessionFactory
from ml.datasets.ml_dataset_processor import MLDatasetProcessor
from ml.datasets.ml_split_processor import MLSplitProcessor
from ml.training.ml_training_processor import MLTrainingProcessor

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

def run_all(spark):
    print(f"\n🚀 Running MLDatasetProcessor")
    MLDatasetProcessor(spark).run()

    print(f"\n🚀 Running MLSplitProcessor")
    MLSplitProcessor(spark).run()

    print(f"\n🚀 Running MLTrainingProcessor")
    MLTrainingProcessor(spark).run()

if __name__ == "__main__":
    spark = SparkSessionFactory.create("ml-process")
    run_all(spark)

    print("\n✅ ML DATASETS READY")
