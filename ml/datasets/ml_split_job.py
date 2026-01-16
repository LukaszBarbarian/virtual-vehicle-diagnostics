# ml/datasets/ml_split_job.py

from pyspark.sql import SparkSession
from infra.spark.spark_session import SparkSessionFactory
from ml.datasets.ml_split_processor import MLSplitProcessor


def main():
    
    spark = SparkSessionFactory.create("ml-split")
    MLSplitProcessor(spark).run()


if __name__ == "__main__":
    main()
