# ml/training/ml_training_processor.py

import mlflow
import mlflow.sklearn
import numpy as np

from pyspark.sql import functions as F
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from pipelines.base.processor import BaseProcessor
from app.app_config import AppConfig
from ml.datasets.feature_config import FEATURE_COLUMNS, TARGET_COLUMN
from pyspark.sql.types import (
    StructType, StructField,
    DoubleType, LongType
)



class MLTrainingProcessor(BaseProcessor):
    """
    Train ML model using Spark for I/O and sklearn for training.
    """

    # --------------------------------------------------
    # READ (Spark I/O)
    # --------------------------------------------------
    def read(self):
        train_df = (
            self.spark.read
            .format("parquet")
            .load(AppConfig.ML_DATASET_TRAIN_PATH)
        )

        test_df = (
            self.spark.read
            .format("parquet")
            .load(AppConfig.ML_DATASET_TEST_PATH)
        )

        return train_df, test_df

    # --------------------------------------------------
    # TRANSFORM (NO-OP)
    # --------------------------------------------------
    def transform(self, dfs):
        return dfs

    # --------------------------------------------------
    # PROCESS (DRIVER-ONLY ML)
    # --------------------------------------------------
    def process(self, dfs):
        train_df, test_df = dfs

        # 🔑 collect ONLY ON DRIVER
        train_pd = train_df.select(
            FEATURE_COLUMNS + [TARGET_COLUMN]
        ).toPandas()

        test_pd = test_df.select(
            FEATURE_COLUMNS + [TARGET_COLUMN]
        ).toPandas()

        X_train = train_pd[FEATURE_COLUMNS]
        y_train = train_pd[TARGET_COLUMN]

        X_test = test_pd[FEATURE_COLUMNS]
        y_test = test_pd[TARGET_COLUMN]

        with mlflow.start_run(run_name="rf_baseline"):
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1,
            )

            model.fit(X_train, y_train)

            preds = model.predict(X_test)

            mae = mean_absolute_error(y_test, preds)
            rmse = np.sqrt(mean_squared_error(y_test, preds))

            # ---- MLflow logging ----
            mlflow.log_param("model_type", "RandomForestRegressor")
            mlflow.log_param("n_estimators", 100)
            mlflow.log_param("max_depth", 10)

            mlflow.log_metric("mae", mae)
            mlflow.log_metric("rmse", rmse)

            mlflow.sklearn.log_model(
                model,
                artifact_path="model"
            )

        return {
            "mae": mae,
            "rmse": rmse,
            "rows_train": len(train_pd),
            "rows_test": len(test_pd),
        }

    # --------------------------------------------------
    # WRITE (optional metrics as Spark DF)
    # --------------------------------------------------
    def write(self, result):
        metrics_df = (
            self.spark
            .range(1)
            .select(
                F.lit(float(result["mae"])).alias("mae"),
                F.lit(float(result["rmse"])).alias("rmse"),
                F.lit(int(result["rows_train"])).alias("rows_train"),
                F.lit(int(result["rows_test"])).alias("rows_test"),
            )
            .withColumn("created_at", F.current_timestamp())
        )

        (
            metrics_df
            .write
            .mode("append")
            .parquet(AppConfig.ML_TRAINING_METRICS_PATH)
        )