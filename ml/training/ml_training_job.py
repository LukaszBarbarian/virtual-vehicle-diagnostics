# ml/training/ml_training_job.py

from infra.spark.spark_session import SparkSessionFactory
from ml.training.ml_training_processor import MLTrainingProcessor


def main():
    spark = SparkSessionFactory.create("ML Training")

    MLTrainingProcessor(spark).run()


if __name__ == "__main__":
    main()
