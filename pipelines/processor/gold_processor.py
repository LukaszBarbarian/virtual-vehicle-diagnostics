from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql import DataFrame

from app.app_config import AppConfig
from pipelines.base.processor import BaseProcessor
from ml.datasets.feature_config import FEATURE_COLUMNS, TARGET_COLUMN, META_COLUMNS

class GoldProcessor(BaseProcessor):
    """
    Final stage of the Medallion architecture. Transforms Silver-tier state data 
    into a curated dataset for Machine Learning, including feature engineering 
    and target labeling.
    """
    TICKS_PER_SEC = 10
    WEAR_WINDOW_SEC = 10
    WEAR_LAG = WEAR_WINDOW_SEC * TICKS_PER_SEC 
    
    def read(self) -> DataFrame:
        """
        Reads structured state data from the Silver Delta table.
        """
        return self.spark.read.format("delta").load(AppConfig.SILVER_STATE_PATH)

    def transform(self, df: DataFrame) -> DataFrame:
        """
        Performs advanced feature engineering using window functions to calculate 
        wear rates and rolling mechanical statistics.
        """
        # Define window specifications for time-series analysis
        lag_window = Window.partitionBy("simulation_id").orderBy("step")
        rolling_window = Window.partitionBy("simulation_id").orderBy("step").rowsBetween(-self.WEAR_LAG, 0)
        lead_window_smooth = Window.partitionBy("simulation_id").orderBy("step").rowsBetween(0, 30)

        # 1. Feature Engineering: Calculate wear rates and future projections
        base_df = df.withColumn(
            "wear_rate_10s",
            (F.col("engine_wear") - F.lag("engine_wear", self.WEAR_LAG).over(lag_window)) / 10.0
        )

        base_df = base_df.withColumn(
            "future_wear_rate", 
            F.avg("wear_rate_10s").over(lead_window_smooth)
        ).filter(F.col("future_wear_rate").isNotNull())

        # 2. Dynamic Thresholding: Calculate label threshold based on distribution (75th percentile)
        stats = base_df.select(F.percentile_approx("future_wear_rate", 0.75).alias("p75")).collect()
        threshold = stats[0]["p75"] if stats and stats[0]["p75"] is not None else 0.0005

        # 3. Aggregated Mechanical Features: Descriptive statistics over 10s windows
        processed_df = (
            base_df
            .withColumn("rpm_avg_10s", F.avg("engine_rpm").over(rolling_window))
            .withColumn("rpm_std_10s", F.stddev("engine_rpm").over(rolling_window))
            .withColumn("throttle_avg_10s", F.avg("throttle").over(rolling_window))
            .withColumn("engine_load_avg_10s", F.avg("load").over(rolling_window))
            .withColumn("power_factor", F.col("engine_rpm") * F.col("load"))
            .withColumn("rpm_range_10s", F.max("engine_rpm").over(rolling_window) - F.min("engine_rpm").over(rolling_window))
            .withColumn("load_max_10s", F.max("load").over(rolling_window))
        )

        # 4. Target Labeling: Classify driving impact as AGGRESSIVE or NORMAL
        return processed_df.withColumn(
            TARGET_COLUMN,
            F.when(F.col("future_wear_rate") > threshold, F.lit("AGGRESSIVE"))
             .otherwise(F.lit("NORMAL"))
        )

    def write(self, df: DataFrame):
        """
        Selects final features and metadata, then persists the curated dataset 
        to the Gold Delta table for ML consumption.
        """
        actual_columns = df.columns
        # Filter columns based on availability and configuration
        selected_cols = [c for c in (META_COLUMNS + FEATURE_COLUMNS + [TARGET_COLUMN]) if c in actual_columns]
        
        df.select(*selected_cols)\
          .write.format("delta").mode("overwrite")\
          .option("overwriteSchema", "true")\
          .save(AppConfig.GOLD_FEATURES_PATH)