from infra.spark.spark_session import SparkSessionFactory
from pipelines.gold.gold_processor import GoldProcessor


def main():
    spark = SparkSessionFactory.create("silver-ml-to-gold")
    GoldProcessor(spark).run()    


if __name__ == "__main__":
    main()
