import sys
sys.path.insert(0, "d:/projects/cv-demo3")
print("sys.path:", sys.path)

from pyspark.sql.functions import (
    col, from_json, window,
    avg, max as spark_max, stddev,
    from_unixtime
)




from streaming.spark.spark_session import SparkService
from streaming.spark.schemas import BaseEventSchema


KAFKA_TOPIC = "simulation.raw"
KAFKA_BROKERS = "localhost:9092"


from pyspark.sql.functions import col

def write_bronze_raw(spark):
    print("🟫 Writing RAW events to BRONZE...")

    raw = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BROKERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "earliest")
        .load()
    )

    # Kafka value → string (JSON)
    bronze_df = raw.select(
        col("timestamp").alias("kafka_ts"),
        col("partition"),
        col("offset"),
        col("value").cast("string").alias("raw_event")
    )

    query = (
        bronze_df.writeStream
        .format("json")
        .outputMode("append")
        .option("path", "abfss://bronze@lsvehicle.dfs.core.windows.net/raw_events")
        .option("checkpointLocation", "abfss://bronze@lsvehicle.dfs.core.windows.net/checkpoints/bronze_raw")
        .trigger(processingTime="5 seconds")
        .start()
    )


    query.awaitTermination()




def main():
    config = None#ConfigManager()
    spark_service = SparkService(config)
    spark = spark_service.start()

    write_bronze_raw(spark)    


if __name__ == "__main__":
    main()
