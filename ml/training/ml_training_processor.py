# ml/training/ml_training_processor.py

import inspect

import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score, roc_auc_score

from app.app_config import AppConfig, LakePaths
from ml.datasets.feature_config import FEATURE_COLUMNS, POSITIVE_CLASS, TARGET_COLUMN
from ml.tracking.mlflow_setup import configure_mlflow
from pipelines.base.processor import BaseProcessor

SKOPS_TRUSTED_TYPES = ["sklearn.tree._tree.Tree"]


class MLTrainingProcessor(BaseProcessor):
    """
    Trains the driving-style classifier, logs it to MLflow and registers it
    as the model served by the cockpit.
    """

    MODEL_PARAMS = {
        "n_estimators": 300,
        "max_depth": 12,
        "class_weight": "balanced",
        "random_state": 42,
    }

    def read(self):
        """
        Loads the train and test splits.
        """
        train_df = self.spark.read.parquet(LakePaths.ML_DATASET_TRAIN_PATH)
        test_df = self.spark.read.parquet(LakePaths.ML_DATASET_TEST_PATH)
        return train_df, test_df

    def process(self, dfs):
        """
        Fits the model and logs parameters, metrics (including a majority-class baseline),
        feature importances and the registered model to MLflow.
        """
        train_df, test_df = dfs

        train_pd = train_df.toPandas().dropna()
        test_pd = test_df.toPandas().dropna()

        X_train, y_train = train_pd[FEATURE_COLUMNS], train_pd[TARGET_COLUMN]
        X_test, y_test = test_pd[FEATURE_COLUMNS], test_pd[TARGET_COLUMN]

        configure_mlflow()
        with mlflow.start_run(run_name="driving_style_random_forest"):
            model = RandomForestClassifier(**self.MODEL_PARAMS)
            model.fit(X_train, y_train)
            preds = model.predict(X_test)

            # A model is only useful if it beats always predicting the majority class
            majority_class = y_train.mode()[0]
            metrics = {
                "accuracy": accuracy_score(y_test, preds),
                "baseline_accuracy": float((y_test == majority_class).mean()),
                "f1_aggressive": f1_score(y_test, preds, pos_label=POSITIVE_CLASS, zero_division=0),
                "train_rows": len(train_pd),
                "test_rows": len(test_pd),
                "test_aggressive_share": float((y_test == POSITIVE_CLASS).mean()),
            }
            if y_test.nunique() == 2 and POSITIVE_CLASS in model.classes_:
                aggressive_idx = list(model.classes_).index(POSITIVE_CLASS)
                metrics["roc_auc"] = roc_auc_score(
                    y_test == POSITIVE_CLASS, model.predict_proba(X_test)[:, aggressive_idx]
                )

            print("\n--- MODEL PERFORMANCE REPORT ---")
            print(classification_report(y_test, preds, zero_division=0))
            for key, value in metrics.items():
                print(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}")

            importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))
            print("\n--- FEATURE IMPORTANCE RANKING ---")
            for feat, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True):
                print(f"{feat}: {imp:.4f}")

            mlflow.log_params(self.MODEL_PARAMS)
            mlflow.log_metrics(metrics)
            mlflow.log_dict(importances, "feature_importance.json")
            log_kwargs = {"registered_model_name": AppConfig.MODEL_NAME, "input_example": X_train.head(5)}
            # Newer MLflow serialises with skops and only loads explicitly trusted types;
            # the trees are created right here, so they are trusted
            if "skops_trusted_types" in inspect.signature(mlflow.sklearn.log_model).parameters:
                log_kwargs["skops_trusted_types"] = SKOPS_TRUSTED_TYPES
            mlflow.sklearn.log_model(model, "model", **log_kwargs)

        return metrics

    def write(self, result):
        """
        Metrics and the model are persisted by MLflow in process().
        """
        return result
