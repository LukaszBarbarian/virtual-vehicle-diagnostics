# ml/training/ml_training_processor.py

import mlflow
import mlflow.sklearn

from pyspark.sql import functions as F
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import classification_report, mean_absolute_error, mean_squared_error, accuracy_score
import numpy as np

from pipelines.base.processor import BaseProcessor
from app.app_config import AppConfig
from ml.datasets.feature_config import FEATURE_COLUMNS, TARGET_COLUMN


class MLTrainingProcessor(BaseProcessor):
    def read(self):
        train_df = self.spark.read.parquet(AppConfig.ML_DATASET_TRAIN_PATH)
        test_df = self.spark.read.parquet(AppConfig.ML_DATASET_TEST_PATH)
        return train_df, test_df

    def process(self, dfs):
        train_df, test_df = dfs

        # Konwersja do Pandas i czyszczenie
        train_pd = train_df.toPandas().dropna()
        test_pd = test_df.toPandas().dropna()

        # Separacja cech i celu
        X_train = train_pd[FEATURE_COLUMNS]
        y_train = train_pd[TARGET_COLUMN]
        X_test = test_pd[FEATURE_COLUMNS]
        y_test = test_pd[TARGET_COLUMN]

        with mlflow.start_run(run_name="driving_style_final_v1"):
            # Używamy standardowego lasu - przy 25% mniejszościowej klasy 
            # 'balanced' w zupełności wystarczy, bez kombinowania z wagami 1:10
            model = RandomForestClassifier(
                n_estimators=300,
                max_depth=12,
                class_weight="balanced",
                random_state=42
            )

            model.fit(X_train, y_train)
            preds = model.predict(X_test)

            # Raport klasyfikacji powie nam całą prawdę
            report = classification_report(y_test, preds)
            print("\n--- WYNIKI MODELU ---")
            print(report)

            # Logowanie do MLflow
            acc = accuracy_score(y_test, preds)
            mlflow.log_metric("accuracy", acc)
            mlflow.sklearn.log_model(model, "model")

            # Wyświetlenie ważności cech (sprawdźmy czy power_factor wygrywa!)
            importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_))
            print("\n--- WAŻNOŚĆ CECH (Co model bierze pod uwagę): ---")
            for feat, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True):
                print(f"{feat}: {imp:.4f}")

        return {"accuracy": acc}

    def write(self, result):
        # ... standardowy zapis metryk jak wcześniej ...
        pass