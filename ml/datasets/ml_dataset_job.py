# ml/datasets/ml_dataset_job.py

from infra.spark.spark_session import SparkSessionFactory
from ml.datasets.ml_dataset_processor import MLDatasetProcessor


def main():
    spark = SparkSessionFactory.create("gold-ml-ds")
    MLDatasetProcessor(spark).run()   


if __name__ == "__main__":
    main()
