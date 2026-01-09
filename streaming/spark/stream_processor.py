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
        .start()
    )


    query.awaitTermination()




def main():
    config = None#ConfigManager()
    spark_service = SparkService(config)
    spark = spark_service.start()

    write_bronze_raw(spark)

    return

    # ---------- READ FROM KAFKA ----------
    raw = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BROKERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .load()
    )

    # ---------- PARSE JSON ----------
    parsed = (
        raw
        .selectExpr("CAST(value AS STRING) as json")
        .select(from_json(col("json"), BaseEventSchema).alias("event"))
        .select("event.*")
        .filter(col("event_type") == "simulation.raw")
    )

    # ---------- EVENT TIME ----------
    with_time = (
        parsed
        .withColumn(
            "event_time",
            from_unixtime(col("timestamp")).cast("timestamp")
        )
    )

    # ---------- FLATTEN ----------
    flat = with_time.select(
        col("event_id"),
        col("event_time"),
        col("payload.modules.engine.engine_rpm").alias("engine_rpm"),
        col("payload.modules.engine.engine_temp_c").alias("engine_temp"),
        col("payload.modules.vehicle.speed_kmh").alias("speed_kmh"),
        col("payload.modules.vehicle.load").alias("load"),
        col("payload.modules.wear.engine_wear").alias("engine_wear"),
    )

    # ---------- WINDOW AGGREGATION ----------
    features = (
        flat
        .withWatermark("event_time", "10 seconds")
        .groupBy(
            window(col("event_time"), "30 seconds", "5 seconds")
        )
        .agg(
            avg("engine_rpm").alias("rpm_mean"),
            spark_max("engine_rpm").alias("rpm_max"),
            stddev("engine_rpm").alias("rpm_std"),
            avg("engine_temp").alias("temp_mean"),
            spark_max("engine_temp").alias("temp_max"),
            avg("speed_kmh").alias("speed_mean"),
            spark_max("engine_wear").alias("engine_wear_max"),
        )
    )

    # ---------- WRITE TO BRONZE ----------
    query = (
        features.writeStream
        .format("json")
        .outputMode("append")
        .option("path", "./data/bronze/features")
        .option("checkpointLocation", "./data/checkpoints/features")
        .trigger(processingTime="5 seconds")
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
