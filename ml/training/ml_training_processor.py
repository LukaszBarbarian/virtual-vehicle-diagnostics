# ml/training/ml_training_processor.py

import mlflow
import mlflow.sklearn
from pyspark.sql import functions as F
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import numpy as np

from pipelines.base.processor import BaseProcessor
from app.app_config import AppConfig
from ml.datasets.feature_config import FEATURE_COLUMNS, TARGET_COLUMN

class MLTrainingProcessor(BaseProcessor):
    """
    Processor responsible for training the Driving Style Classification model.
    Utilizes MLflow for experiment tracking and scikit-learn for model logic.
    """

    def read(self):
        """
        Loads pre-processed training and testing datasets from the Gold layer.
        """
        train_df = self.spark.read.parquet(AppConfig.ML_DATASET_TRAIN_PATH)
        test_df = self.spark.read.parquet(AppConfig.ML_DATASET_TEST_PATH)
        return train_df, test_df

    def process(self, dfs):
        """
        Main ML pipeline: data conversion, training with class balancing, 
        and experiment logging to MLflow.
        """
        train_df, test_df = dfs

        # Convert to Pandas for scikit-learn compatibility and handle missing values
        train_pd = train_df.toPandas().dropna()
        test_pd = test_df.toPandas().dropna()

        # Feature-Target separation
        X_train = train_pd[FEATURE_COLUMNS]
        y_train = train_pd[TARGET_COLUMN]
        X_test = test_pd[FEATURE_COLUMNS]
        y_test = test_pd[TARGET_COLUMN]

        with mlflow.start_run(run_name="driving_style_classification_v1"):
            # Initialize RandomForest with 'balanced' weights to handle class distribution
            model = RandomForestClassifier(
                n_estimators=300,
                max_depth=12,
                class_weight="balanced",
                random_state=42
            )

            # Train the model
            model.fit(X_train, y_train)
            preds = model.predict(X_test)

            # Generate performance report
            report = classification_report(y_test, preds)
            print("\n--- MODEL PERFORMANCE REPORT ---")
            print(report)

            # Log metrics and the serialized model to MLflow registry
            acc = accuracy_score(y_test, preds)
            mlflow.log_metric("accuracy", acc)
            mlflow.sklearn.log_model(model, "driving_style_model")

            # Extract and log feature importance
            importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_))
            print("\n--- FEATURE IMPORTANCE RANKING ---")
            for feat, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True):
                print(f"{feat}: {imp:.4f}")
                mlflow.log_param(f"importance_{feat}", imp)

        return {"accuracy": acc}

    def write(self, result):
        """
        Placeholder for persisting specific run metrics or metadata into a database.
        """
        pass