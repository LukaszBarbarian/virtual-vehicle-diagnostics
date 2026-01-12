from pyspark.sql import functions as F
from pyspark.sql.types import *

from app.app_config import AppConfig
from pipelines.base.processor import BaseProcessor


class SilverProcessor(BaseProcessor):

    # ---------- 1️⃣ READ BRONZE ----------
    def read(self):
        return (
            self.spark.read
            .format("json")
            .load(AppConfig.BRONZE_RAW_PATH)
        )

    # ---------- 2️⃣ MAIN PROCESS ----------
    def process(self, bronze_df):
        parsed = self._parse_raw_event(bronze_df)
        silver = self._project_silver(parsed)
        checked = self._apply_quality_checks(silver)

        valid_df, quarantine_df = self._split_valid_quarantine(checked)

        self._write_quarantine(quarantine_df)
        self._write_metrics(checked)

        return valid_df

    # ---------- 3️⃣ WRITE SILVER ----------
    def write(self, silver_df):
        (
            silver_df
            .write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .save(AppConfig.SILVER_STATE_PATH)
        )

    # ============================================================
    # ===================== INTERNAL STEPS =======================
    # ============================================================

    def _parse_raw_event(self, bronze_df):
        raw_schema = StructType([
            StructField("event_type", StringType()),
            StructField("event_version", IntegerType()),
            StructField("event_id", StringType()),
            StructField("timestamp", DoubleType()),
            StructField("payload", StructType([
                StructField("time", DoubleType()),
                StructField("step", IntegerType()),
                StructField("modules", StructType([
                    StructField("engine", StructType([
                        StructField("engine_rpm", DoubleType()),
                        StructField("engine_temp_c", DoubleType())
                    ])),
                    StructField("gearbox", StructType([
                        StructField("current_gear", IntegerType())
                    ])),
                    StructField("vehicle", StructType([
                        StructField("speed_kmh", DoubleType())
                    ])),
                    StructField("driver", StructType([
                        StructField("throttle", DoubleType()),
                        StructField("brake", DoubleType())
                    ])),
                    StructField("wear", StructType([
                        StructField("engine_wear", DoubleType()),
                        StructField("gearbox_wear", DoubleType())
                    ]))
                ]))
            ]))
        ])

        return bronze_df.withColumn(
            "parsed",
            F.from_json("raw_event", raw_schema)
        )

    def _project_silver(self, parsed_df):
        return (
            parsed_df
            .select(
                F.col("parsed.payload.step").alias("step"),
                F.col("parsed.payload.time").alias("simulation_time"),

                F.col("parsed.payload.modules.engine.engine_rpm").alias("rpm"),
                F.col("parsed.payload.modules.vehicle.speed_kmh").alias("speed_kmh"),
                F.col("parsed.payload.modules.driver.throttle").alias("throttle"),
                F.col("parsed.payload.modules.driver.brake").alias("brake"),
                F.col("parsed.payload.modules.gearbox.current_gear").alias("gear"),

                F.col("parsed.payload.modules.engine.engine_temp_c").alias("engine_temp_c"),
                F.col("parsed.payload.modules.wear.engine_wear").alias("wear_engine"),
                F.col("parsed.payload.modules.wear.gearbox_wear").alias("wear_gearbox"),

                F.current_timestamp().alias("created_at")
            )
        )

    def _apply_quality_checks(self, df):
        return (
            df
            .withColumn(
                "is_null_violation",
                F.expr("""
                    step IS NULL OR
                    simulation_time IS NULL OR
                    rpm IS NULL OR
                    speed_kmh IS NULL OR
                    gear IS NULL
                """)
            )
            .withColumn(
                "is_range_violation",
                F.expr("""
                    rpm < 0 OR rpm > 9000 OR
                    speed_kmh < 0 OR speed_kmh > 400 OR
                    throttle < 0 OR throttle > 1 OR
                    brake < 0 OR brake > 1 OR
                    engine_temp_c < -40 OR engine_temp_c > 200 OR
                    wear_engine < 0 OR wear_engine > 1 OR
                    wear_gearbox < 0 OR wear_gearbox > 1
                """)
            )
            .withColumn(
                "is_logical_violation",
                F.expr("""
                    (speed_kmh > 0 AND gear = 0)
                """)
            )
            .withColumn(
                "is_valid",
                ~(
                    F.col("is_null_violation") |
                    F.col("is_range_violation") |
                    F.col("is_logical_violation")
                )
            )
        )

    def _split_valid_quarantine(self, df):
        valid_df = (
            df.filter("is_valid = true")
            .drop(
                "is_null_violation",
                "is_range_violation",
                "is_logical_violation",
                "is_valid"
            )
        )

        quarantine_df = df.filter("is_valid = false")

        return valid_df, quarantine_df

    def _write_quarantine(self, quarantine_df):
        (
            quarantine_df
            .write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .save(AppConfig.SILVER_QUARANTINE_PATH)
        )

    def _write_metrics(self, df):
        metrics_df = (
            df.groupBy()
            .agg(
                F.count("*").alias("total_rows"),
                F.sum(F.col("is_null_violation").cast("int")).alias("null_violations"),
                F.sum(F.col("is_range_violation").cast("int")).alias("range_violations"),
                F.sum(F.col("is_logical_violation").cast("int")).alias("logical_violations"),
                F.sum((~F.col("is_valid")).cast("int")).alias("invalid_rows")
            )
            .withColumn("dataset", F.lit("silver_vehicle_telemetry"))
            .withColumn("check_time", F.current_timestamp())
        )

        (
            metrics_df
            .write
            .format("delta")
            .mode("append")
            .save(AppConfig.DATA_QUALITY_METRICS_PATH)
        )
