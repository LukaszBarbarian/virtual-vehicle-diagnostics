from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from app.app_config import LakePaths
from ml.datasets.feature_config import (
    AGGRESSIVE_PERCENTILE,
    FEATURE_COLUMNS,
    META_COLUMNS,
    POSITIVE_CLASS,
    TARGET_COLUMN,
    WINDOW_LAG,
    WINDOW_SEC,
)
from pipelines.base.processor import BaseProcessor


class GoldProcessor(BaseProcessor):
    """
    Final stage of the Medallion architecture. Turns Silver telemetry into a curated
    ML dataset for a virtual wear sensor: rolling features over the past 10 seconds
    and a label describing how fast the engine wore during those same 10 seconds.
    """

    def read(self) -> DataFrame:
        """
        Reads structured state data from the Silver Delta table.
        """
        return self.spark.read.format("delta").load(LakePaths.SILVER_STATE_PATH)

    def transform(self, df: DataFrame) -> DataFrame:
        """
        Builds the 10-second window features and the wear-rate label.
        """
        ordered = Window.partitionBy("simulation_id").orderBy("step")
        past_window = ordered.rowsBetween(-WINDOW_LAG, 0)

        # 1. Features: descriptive statistics over the last 10 seconds (identical to the live engine)
        features = (
            df
            .withColumn("rpm_avg_10s", F.avg("engine_rpm").over(past_window))
            .withColumn("rpm_std_10s", F.stddev("engine_rpm").over(past_window))
            .withColumn("throttle_avg_10s", F.avg("throttle").over(past_window))
            .withColumn("engine_load_avg_10s", F.avg("load").over(past_window))
            .withColumn("power_factor", F.col("engine_rpm") * F.col("load"))
            .withColumn("rpm_range_10s", F.max("engine_rpm").over(past_window) - F.min("engine_rpm").over(past_window))
            .withColumn("load_max_10s", F.max("load").over(past_window))
            .withColumn("rpm_max_10s", F.max("engine_rpm").over(past_window))
        )

        # 2. Label source: engine wear accumulated over the same window. Wear itself is not a
        #    feature: a real car cannot measure it, the model estimates it from observable signals.
        #    Ticks without a full 10-second history are dropped, as the live engine waits for them.
        labelled = (
            features
            .withColumn(
                "wear_rate_10s",
                (F.col("engine_wear") - F.lag("engine_wear", WINDOW_LAG).over(ordered)) / WINDOW_SEC
            )
            .filter(F.col("wear_rate_10s").isNotNull())
        )

        # 3. Dynamic threshold: the top share of wear rates is labelled AGGRESSIVE
        stats = labelled.select(
            F.percentile_approx("wear_rate_10s", AGGRESSIVE_PERCENTILE).alias("threshold")
        ).collect()
        threshold = stats[0]["threshold"] if stats and stats[0]["threshold"] is not None else 0.0005

        # 4. Target labelling
        return labelled.withColumn(
            TARGET_COLUMN,
            F.when(F.col("wear_rate_10s") > threshold, F.lit(POSITIVE_CLASS)).otherwise(F.lit("NORMAL"))
        )

    def process(self, df: DataFrame) -> DataFrame:
        return df

    def write(self, df: DataFrame):
        """
        Persists metadata, features and label to the Gold Delta table (full rebuild, idempotent).
        """
        (
            df.select(*META_COLUMNS, *FEATURE_COLUMNS, TARGET_COLUMN)
            .write.format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .save(LakePaths.GOLD_FEATURES_PATH)
        )
