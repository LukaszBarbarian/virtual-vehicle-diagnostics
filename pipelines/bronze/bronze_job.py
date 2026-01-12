from infra.spark.spark_session import SparkSessionFactory
from pipelines.bronze.bronze_processor import BronzeProcessor


def main():
    spark = SparkSessionFactory.create("bronze-kafka-ingestion")
    BronzeProcessor(spark).run()


if __name__ == "__main__":
    main()
