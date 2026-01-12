from pyspark.sql import functions as F
from pyspark.sql.window import Window

from app.app_config import AppConfig
from pipelines.base.processor import BaseProcessor


class GoldProcessor(BaseProcessor):

    def read(self):
        return (
            self.spark.read
            .format("delta")
            .load(AppConfig.SILVER_STATE_PATH)
        )

    def process(self, silver_df):

        # zakładamy stały krok czasu symulacji (np. 0.1s)
        window_30 = Window.orderBy("step").rowsBetween(-300, 0)
        window_60 = Window.orderBy("step").rowsBetween(-600, 0)

        gold_df = (
            silver_df
            .withColumn("rpm_avg_30s", F.avg("rpm").over(window_30))
            .withColumn("rpm_std_30s", F.stddev("rpm").over(window_30))
            .withColumn("rpm_avg_60s", F.avg("rpm").over(window_60))
            .withColumn("rpm_delta_30s", F.col("rpm") - F.lag("rpm", 300).over(Window.orderBy("step")))

            .withColumn("engine_temp_avg_30s", F.avg("engine_temp_c").over(window_30))
            .withColumn("engine_temp_delta_30s", F.col("engine_temp_c") - F.lag("engine_temp_c", 300).over(Window.orderBy("step")))

            .withColumn("throttle_avg_30s", F.avg("throttle").over(window_30))
            .withColumn("throttle_std_30s", F.stddev("throttle").over(window_30))

            .withColumn("wear_engine_delta_60s", F.col("wear_engine") - F.lag("wear_engine", 600).over(Window.orderBy("step")))

            .withColumn("created_at", F.current_timestamp())
        )

        return gold_df

    def write(self, gold_df):
        (
            gold_df
            .write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .save(AppConfig.GOLD_FEATURES_PATH)
        )
