from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from app.app_config import LakePaths
from ml.datasets.feature_config import (
    AGGRESSIVE_PERCENTILE,
    FEATURE_COLUMNS,
    LABEL_HORIZON_SEC,
    LABEL_HORIZON_TICKS,
    META_COLUMNS,
    POSITIVE_CLASS,
    TARGET_COLUMN,
    WINDOW_LAG,
)
from pipelines.base.processor import BaseProcessor


class GoldProcessor(BaseProcessor):
    """
    Final stage of the Medallion architecture. Turns Silver telemetry into a curated
    ML dataset: rolling features over the past 10 seconds and a label describing
    the engine wear of the next 10 seconds.
    """

    def read(self) -> DataFrame:
        """
        Reads structured state data from the Silver Delta table.
        """
        return self.spark.read.format("delta").load(LakePaths.SILVER_STATE_PATH)

    def transform(self, df: DataFrame) -> DataFrame:
        """
        Builds the past-window features and the future-wear label.
        """
        ordered = Window.partitionBy("simulation_id").orderBy("step")
        past_window = ordered.rowsBetween(-WINDOW_LAG, 0)

        # 1. Label source: wear accumulated strictly after the current tick
        labelled = (
            df
            .withColumn(
                "future_wear_rate",
                (F.lead("engine_wear", LABEL_HORIZON_TICKS).over(ordered) - F.col("engine_wear")) / LABEL_HORIZON_SEC
            )
            .filter(F.col("future_wear_rate").isNotNull())
        )

        # 2. Dynamic threshold: the top share of future wear rates is labelled AGGRESSIVE
        stats = labelled.select(
            F.percentile_approx("future_wear_rate", AGGRESSIVE_PERCENTILE).alias("threshold")
        ).collect()
        threshold = stats[0]["threshold"] if stats and stats[0]["threshold"] is not None else 0.0005

        # 3. Features: descriptive statistics over the past 10 seconds (identical to the live engine)
        features = (
            labelled
            .withColumn("rpm_avg_10s", F.avg("engine_rpm").over(past_window))
            .withColumn("rpm_std_10s", F.stddev("engine_rpm").over(past_window))
            .withColumn("throttle_avg_10s", F.avg("throttle").over(past_window))
            .withColumn("engine_load_avg_10s", F.avg("load").over(past_window))
            .withColumn("power_factor", F.col("engine_rpm") * F.col("load"))
            .withColumn("rpm_range_10s", F.max("engine_rpm").over(past_window) - F.min("engine_rpm").over(past_window))
            .withColumn("load_max_10s", F.max("load").over(past_window))
        )

        # Keep only ticks with a full 10-second history, as the live engine does
        features = features.withColumn("_row", F.row_number().over(ordered)).filter(F.col("_row") > WINDOW_LAG)

        # 4. Target labelling
        return features.withColumn(
            TARGET_COLUMN,
            F.when(F.col("future_wear_rate") > threshold, F.lit(POSITIVE_CLASS)).otherwise(F.lit("NORMAL"))
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
