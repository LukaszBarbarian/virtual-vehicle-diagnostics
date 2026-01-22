from pyspark.sql import functions as F
from pyspark.sql.window import Window

from app.app_config import AppConfig
from pipelines.base.processor import BaseProcessor

PREDICTION_HORIZON = 30
class GoldProcessor(BaseProcessor):

    def read(self):
        return (
            self.spark.read
            .format("delta")
            .load(AppConfig.SILVER_STATE_PATH)
        )

    def _add_engine_health_score(self, df):
        return (
            df
            .withColumn(
                "engine_health_score",
                F.expr("""
                    greatest(
                        0,
                        100
                        - least(40, abs(rpm_delta_30s) / 100)
                        - least(30, abs(coolant_temp_c_delta_30s) * 2)
                        - least(30, wear_engine_delta_60s * 1000)
                    )
                """)
            )
        )


    # --------------------------------------------------
    # Sanity / quality rules for Gold
    # --------------------------------------------------
    def _sanity_data(self, df):
        return (
            df
            .withColumn(
                "is_gold_sane",
                F.expr("""
                    rpm_std_30s >= 0 AND
                    throttle_std_30s >= 0 AND
                    (
                        has_full_window_30s = false OR
                        (
                            rpm_delta_30s IS NOT NULL AND
                            abs(rpm_delta_30s) <= 5000
                        )
                    )
                """)
            )
        )

    # --------------------------------------------------
    # Main Gold processing
    # --------------------------------------------------
    def process(self, silver_df):

        # 🔑 OKNA TYLKO W RAMACH JEDNEJ SYMULACJI
        window_30 = (
            Window
            .partitionBy("simulation_id")
            .orderBy("step")
            .rowsBetween(-300, 0)
        )

        window_60 = (
            Window
            .partitionBy("simulation_id")
            .orderBy("step")
            .rowsBetween(-600, 0)
        )

        lag_window = (
            Window
            .partitionBy("simulation_id")
            .orderBy("step")
        )

        gold_df = (
            silver_df
            # --- RPM ---
            .withColumn("rpm_avg_30s", F.avg("rpm").over(window_30))
            .withColumn("rpm_std_30s", F.stddev("rpm").over(window_30))
            .withColumn("rpm_avg_60s", F.avg("rpm").over(window_60))
            .withColumn(
                "rpm_delta_30s",
                F.col("rpm") - F.lag("rpm", 300).over(lag_window)
            )

            # --- COOLANT ---
            .withColumn(
                "coolant_temp_c_avg_30s",
                F.avg("coolant_temp_c").over(window_30)
            )
            .withColumn(
                "coolant_temp_c_delta_30s",
                F.col("coolant_temp_c") - F.lag("coolant_temp_c", 300).over(lag_window)
            )

            # --- THROTTLE ---
            .withColumn("throttle_avg_30s", F.avg("throttle").over(window_30))
            .withColumn("throttle_std_30s", F.stddev("throttle").over(window_30))

            # --- WEAR ---
            .withColumn(
                "wear_engine_delta_60s",
                F.col("wear_engine") - F.lag("wear_engine", 600).over(lag_window)
            )

            # --- WINDOW FLAGS ---
            .withColumn("has_full_window_30s", F.col("step") >= 300)
            .withColumn("has_full_window_60s", F.col("step") >= 600)

            # --- METADATA ---
            .withColumn("record_ts", F.current_timestamp())
            .withColumn("date", F.to_date("created_at"))
            .withColumn("sequence_id", F.concat_ws("_", F.col("simulation_id"), F.col("step"))) # Dodany )
            .withColumn("driver_aggression_30s", 
                (F.stddev("throttle").over(window_30) + F.stddev("brake").over(window_30)) / 2
            )
            .withColumn("thermal_stress_index", F.abs(F.col("oil_temp_c") - F.col("coolant_temp_c")))

        )

        gold_df = self._add_engine_health_score(gold_df)

        # --------------------------------------------------
        # FUTURE TARGET (ML)
        # --------------------------------------------------
        gold_df = gold_df.withColumn(
            "engine_health_score_future",
            F.lead(
                "engine_health_score",
                PREDICTION_HORIZON
            ).over(lag_window)
        )

        # opcjonalna, ale BARDZO dobra flaga
        gold_df = gold_df.withColumn(
            "has_future_label",
            F.col("engine_health_score_future").isNotNull()
        )

        gold_df = self._sanity_data(gold_df)
        return gold_df


    # --------------------------------------------------
    # Write Gold
    # --------------------------------------------------
    def write(self, gold_df):
        (
            gold_df
            .write
            .format("delta")
            .mode("append")    
            .option("mergeSchema", "true")
            .partitionBy("simulation_id")    # ❗ logiczna partycja
            .save(AppConfig.GOLD_FEATURES_PATH)
        )
