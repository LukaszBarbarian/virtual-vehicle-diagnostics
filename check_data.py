from pyspark.sql import functions as F
from app.app_config import AppConfig
from infra.spark.spark_session import SparkSessionFactory

# --------------------------------------------------
# READ DATA
# --------------------------------------------------


spark = SparkSessionFactory.create("pipelines-process")

df = (
    spark.read
    .parquet(AppConfig.ML_DATASET_FULL_PATH)
)

print("\n==============================")
print("BASIC INFO")
print("==============================")
df.printSchema()
print(f"Total rows: {df.count()}")

# --------------------------------------------------
# STEP 1: BASIC STATISTICS
# --------------------------------------------------
print("\n==============================")
print("STEP 1: WEAR_RATE STATISTICS")
print("==============================")

stats_df = df.select(
    F.count("*").alias("rows"),
    F.mean("wear_rate").alias("mean_wear_rate"),
    F.stddev("wear_rate").alias("std_wear_rate"),
    F.min("wear_rate").alias("min_wear_rate"),
    F.max("wear_rate").alias("max_wear_rate")
)

stats_df.show(truncate=False)

# --------------------------------------------------
# STEP 2: DISTRIBUTION (DESCRIBE)
# --------------------------------------------------
print("\n==============================")
print("STEP 2: WEAR_RATE DISTRIBUTION")
print("==============================")

df.select("wear_rate").describe().show()

# --------------------------------------------------
# STEP 3: PERCENTILES
# --------------------------------------------------
print("\n==============================")
print("STEP 3: WEAR_RATE PERCENTILES")
print("==============================")

df.select(
    F.expr("percentile_approx(wear_rate, 0.5)").alias("p50"),
    F.expr("percentile_approx(wear_rate, 0.75)").alias("p75"),
    F.expr("percentile_approx(wear_rate, 0.9)").alias("p90"),
    F.expr("percentile_approx(wear_rate, 0.95)").alias("p95"),
    F.expr("percentile_approx(wear_rate, 0.99)").alias("p99")
).show(truncate=False)

# --------------------------------------------------
# STEP 4: CORRELATIONS WITH SELECTED FEATURES
# --------------------------------------------------
print("\n==============================")
print("STEP 4: CORRELATIONS")
print("==============================")

features_to_check = [
    "rpm_avg_10s",
    "rpm_std_10s",
    "engine_load_avg_10s",
    "throttle_avg_10s",
    "throttle_rate_max_10s",
    "oil_temp_c",
    "coolant_temp_c",
]

for feature in features_to_check:
    corr = df.stat.corr(feature, "wear_rate")
    print(f"Correlation wear_rate vs {feature}: {corr:.4f}")

# --------------------------------------------------
# STEP 5: LOW vs HIGH WEAR COMPARISON
# --------------------------------------------------
print("\n==============================")
print("STEP 5: LOW vs HIGH WEAR COMPARISON")
print("==============================")

wear_quantiles = df.select(
    F.expr("percentile_approx(wear_rate, 0.1)").alias("low_wear"),
    F.expr("percentile_approx(wear_rate, 0.9)").alias("high_wear")
).collect()[0]

low_wear = wear_quantiles["low_wear"]
high_wear = wear_quantiles["high_wear"]

print(f"Low wear (10th percentile): {low_wear}")
print(f"High wear (90th percentile): {high_wear}")

if low_wear and high_wear:
    print(f"Wear ratio (high / low): {high_wear / low_wear:.2f}")
else:
    print("Cannot compute wear ratio (zero or null values).")

# --------------------------------------------------
# STEP 6: GROUPED FEATURE MEANS (OPTIONAL BUT VERY TELLING)
# --------------------------------------------------
print("\n==============================")
print("STEP 6: FEATURE MEANS FOR LOW vs HIGH WEAR")
print("==============================")

df_with_bucket = (
    df
    .withColumn(
        "wear_bucket",
        F.when(F.col("wear_rate") <= low_wear, F.lit("LOW"))
         .when(F.col("wear_rate") >= high_wear, F.lit("HIGH"))
         .otherwise(F.lit("MID"))
    )
)

(
    df_with_bucket
    .filter(F.col("wear_bucket").isin("LOW", "HIGH"))
    .groupBy("wear_bucket")
    .agg(
        F.mean("rpm_avg_10s").alias("rpm_avg"),
        F.mean("engine_load_avg_10s").alias("load_avg"),
        F.mean("throttle_avg_10s").alias("throttle_avg"),
        F.mean("throttle_rate_max_10s").alias("throttle_rate_max"),
        F.mean("oil_temp_c").alias("oil_temp_avg"),
        F.mean("coolant_temp_c").alias("coolant_temp_avg"),
        F.mean("wear_rate").alias("wear_rate_avg"),
    )
    .orderBy("wear_bucket")
    .show(truncate=False)
)

print("\nEDA COMPLETE.")
