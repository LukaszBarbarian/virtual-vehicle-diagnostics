from infra.spark.spark_session import SparkSessionFactory
from pipelines.silver.silver_processor import SilverProcessor


def main():
    spark = SparkSessionFactory.create("silver-bronze-to-silver")
    SilverProcessor(spark).run()    


if __name__ == "__main__":
    main()
