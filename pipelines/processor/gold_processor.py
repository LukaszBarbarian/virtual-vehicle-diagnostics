from pyspark.sql import functions as F
from pyspark.sql.window import Window

from app.app_config import AppConfig
from pipelines.base.processor import BaseProcessor
from ml.datasets.feature_config import FEATURE_COLUMNS, TARGET_COLUMN, META_COLUMNS

class GoldProcessor(BaseProcessor):
    TICKS_PER_SEC = 10
    WEAR_WINDOW_SEC = 10  # Okno do wyliczenia chwilowego zużycia
    WEAR_LAG = WEAR_WINDOW_SEC * TICKS_PER_SEC 
    
    def read(self):
        # Pobieramy dane z warstwy Silver
        return self.spark.read.format("delta").load(AppConfig.SILVER_STATE_PATH)

    def transform(self, df):
        lag_window = Window.partitionBy("simulation_id").orderBy("step")
        rolling_window = Window.partitionBy("simulation_id").orderBy("step").rowsBetween(-self.WEAR_LAG, 0)

        # 1. Wear Rate + Future Label (Lead)
        base_df = df.withColumn(
            "wear_rate_10s",
            (F.col("engine_wear") - F.lag("engine_wear", self.WEAR_LAG).over(lag_window)) / 10.0
        )

        lead_window_smooth = Window.partitionBy("simulation_id").orderBy("step").rowsBetween(0, 30)

        base_df = base_df.withColumn(
            "future_wear_rate", 
            F.avg("wear_rate_10s").over(lead_window_smooth)
        ).filter(F.col("future_wear_rate").isNotNull())

        # 2. Dynamically calculate threshold
        stats = base_df.select(F.percentile_approx("future_wear_rate", 0.75).alias("p75")).collect()
        threshold = stats[0]["p75"] if stats and stats[0]["p75"] is not None else 0.0005

        # 3. Features - TUTAJ DODAŁEM BRAKUJĄCE KOLUMNY
        processed_df = (
            base_df
            .withColumn("rpm_avg_10s", F.avg("engine_rpm").over(rolling_window))
            .withColumn("rpm_std_10s", F.stddev("engine_rpm").over(rolling_window)) # DODANE
            .withColumn("throttle_avg_10s", F.avg("throttle").over(rolling_window)) # DODANE
            .withColumn("engine_load_avg_10s", F.avg("load").over(rolling_window))  # DODANE
            .withColumn("power_factor", F.col("engine_rpm") * F.col("load"))       # DODANE
            .withColumn("rpm_range_10s", F.max("engine_rpm").over(rolling_window) - F.min("engine_rpm").over(rolling_window))
            .withColumn("load_max_10s", F.max("load").over(rolling_window))
        )

        return processed_df.withColumn(
            TARGET_COLUMN,
            F.when(F.col("future_wear_rate") > threshold, F.lit("AGGRESSIVE"))
             .otherwise(F.lit("NORMAL"))
        )

    def write(self, df):
        # Sprawdzamy jakie kolumny faktycznie mamy w DataFrame
        actual_columns = df.columns
        # Wybieramy tylko te, które są zdefiniowane w konfiguracji i istnieją w DF
        selected_cols = [c for c in (META_COLUMNS + FEATURE_COLUMNS + [TARGET_COLUMN]) if c in actual_columns]
        
        print(f"--- Zapisywanie kolumn do tabeli Gold: {selected_cols} ---")

        df.select(*selected_cols)\
          .write.format("delta").mode("overwrite")\
          .option("overwriteSchema", "true")\
          .save(AppConfig.GOLD_FEATURES_PATH)