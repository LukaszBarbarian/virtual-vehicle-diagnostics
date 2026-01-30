from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.sql.window import Window

from app.app_config import AppConfig
from pipelines.base.processor import BaseProcessor


class SilverProcessor(BaseProcessor):
    """
    SilverProcessor: Processes raw telemetry data from Bronze into validated, 
    structured Silver layer. English method descriptions applied as requested.
    """

    # ---------- 1️⃣ READ BRONZE ----------
    def read(self):
        """Reads raw JSON events from the Bronze layer."""
        return (
            self.spark.read
            .format("json")
            .load(AppConfig.BRONZE_RAW_PATH)
        )

    # ---------- 2️⃣ MAIN PROCESS ----------
    def process(self, bronze_df):
        """Main transformation pipeline: parsing, projecting, and quality control."""
        parsed = self._parse_raw_event(bronze_df)
        silver = self._project_silver(parsed)
        checked = self._apply_quality_checks(silver)

        valid_df, quarantine_df = self._split_valid_quarantine(checked)

        self._write_quarantine(quarantine_df)
        self._write_metrics(checked)

        return valid_df

    # ---------- 3️⃣ WRITE SILVER ----------
    def write(self, silver_df):
        """Writes validated data to Delta table partitioned by simulation_id."""
        (
            silver_df
            .write
            .format("delta")
            .mode("append")
            .partitionBy("simulation_id")
            .save(AppConfig.SILVER_STATE_PATH)
        )

    # ============================================================
    # ===================== INTERNAL STEPS =======================
    # ============================================================

    def _parse_raw_event(self, bronze_df):
        """Parses the raw JSON string into a structured Spark schema."""
        raw_schema = StructType([
            StructField("event_type", StringType()),
            StructField("event_version", IntegerType()),
            StructField("event_id", StringType()),
            StructField("timestamp", DoubleType()),
            StructField("payload", StructType([
                StructField("simulation_id", StringType()),
                StructField("time", DoubleType()),
                StructField("step", IntegerType()),
                StructField("modules", StructType([
                    StructField("engine", StructType([
                        StructField("engine_rpm", DoubleType())
                    ])),
                    StructField("thermals", StructType([
                        StructField("coolant_temp_c", DoubleType()),
                        StructField("oil_temp_c", DoubleType())
                    ])),
                    StructField("gearbox", StructType([
                        StructField("current_gear", IntegerType())
                    ])),
                    StructField("vehicle", StructType([
                        StructField("speed_kmh", DoubleType()),
                        StructField("load", DoubleType()) # Added missing load field
                    ])),
                    StructField("driver", StructType([
                        StructField("throttle", DoubleType()),
                        StructField("brake", DoubleType()),
                        StructField("throttle_rate", DoubleType()) # Added missing throttle_rate
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
        """Flattens the nested structure and renames columns to match Gold layer expectations."""
        lag_window = Window.partitionBy("simulation_id").orderBy("step")

        return (
            parsed_df
            .select(
                F.col("parsed.payload.simulation_id").alias("simulation_id"),
                F.col("parsed.payload.step").alias("step"),
                F.col("parsed.payload.time").alias("simulation_time"),

                # Renamed to match GoldProcessor expectations
                F.col("parsed.payload.modules.engine.engine_rpm").alias("engine_rpm"),
                F.col("parsed.payload.modules.vehicle.speed_kmh").alias("speed_kmh"),
                F.col("parsed.payload.modules.vehicle.load").alias("load"),
                
                F.col("parsed.payload.modules.driver.throttle").alias("throttle"),
                F.col("parsed.payload.modules.driver.brake").alias("brake"),
                F.col("parsed.payload.modules.driver.throttle_rate").alias("throttle_rate"),
                
                F.col("parsed.payload.modules.gearbox.current_gear").alias("current_gear"),

                F.col("parsed.payload.modules.thermals.coolant_temp_c").alias("coolant_temp_c"),
                F.col("parsed.payload.modules.thermals.oil_temp_c").alias("oil_temp_c"),

                F.col("parsed.payload.modules.wear.engine_wear").alias("engine_wear"),
                F.col("parsed.payload.modules.wear.gearbox_wear").alias("gearbox_wear"),

                F.current_timestamp().alias("processed_at")
            )
        )

    def _apply_quality_checks(self, df):
        """Performs data validation and flags records that violate rules."""
        return (
            df
            .withColumn(
                "is_null_violation",
                F.expr("""
                    simulation_id IS NULL OR
                    step IS NULL OR
                    engine_rpm IS NULL OR
                    speed_kmh IS NULL
                """)
            )
            .withColumn(
                "is_range_violation",
                F.expr("""
                    engine_rpm < 0 OR engine_rpm > 10000 OR
                    speed_kmh < 0 OR speed_kmh > 500 OR
                    throttle < 0 OR throttle > 1.1 OR
                    coolant_temp_c < -50 OR coolant_temp_c > 250
                """)
            )
            .withColumn(
                "is_logical_violation",
                # Relaxed logic: speed > 0 and gear = 0 is now allowed due to shifting states
                F.lit(False) 
            )
            .withColumn(
                "is_valid",
                ~(F.col("is_null_violation") | F.col("is_range_violation") | F.col("is_logical_violation"))
            )
        )

    def _split_valid_quarantine(self, df):
        """Separates valid data from invalid records based on quality flags."""
        valid_df = (
            df.filter("is_valid = true")
            .drop("is_null_violation", "is_range_violation", "is_logical_violation", "is_valid")
        )

        quarantine_df = df.filter("is_valid = false")
        return valid_df, quarantine_df

    def _write_quarantine(self, quarantine_df):
        """Saves invalid records to a quarantine Delta table for further inspection."""
        (
            quarantine_df
            .write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .save(AppConfig.SILVER_QUARANTINE_PATH)
        )

    def _write_metrics(self, df):
        """Logs data quality metrics for monitoring purposes."""
        metrics_df = (
            df.groupBy()
            .agg(
                F.count("*").alias("total_rows"),
                F.sum(F.col("is_null_violation").cast("int")).alias("null_violations"),
                F.sum(F.col("is_range_violation").cast("int")).alias("range_violations"),
                F.sum((~F.col("is_valid")).cast("int")).alias("invalid_rows")
            )
            .withColumn("dataset", F.lit("silver_telemetry"))
            .withColumn("check_time", F.current_timestamp())
        )

        metrics_df.write.format("delta").mode("append").save(AppConfig.DATA_QUALITY_METRICS_PATH)