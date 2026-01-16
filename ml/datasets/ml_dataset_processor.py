# ml/datasets/ml_dataset_processor.py

from pyspark.sql import functions as F

from pipelines.base.processor import BaseProcessor
from app.app_config import AppConfig
from ml.datasets.feature_config import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    META_COLUMNS
)

class MLDatasetProcessor(BaseProcessor):

    def read(self):
        return (
            self.spark.read
            .format("delta")
            .load(AppConfig.GOLD_FEATURES_PATH)
        )

    def transform(self, df):
        return df

    def process(self, df):
        return (
            df
            .filter("is_gold_sane = true")
            .filter("has_full_window_30s = true")
            .filter(F.col(TARGET_COLUMN).isNotNull())
            .select(
                *(META_COLUMNS + FEATURE_COLUMNS + [TARGET_COLUMN])
            )
        )

    def write(self, df):
        (
            df
            .write
            .format("parquet")     # ← ML-friendly
            .mode("overwrite")
            .save(AppConfig.ML_DATASET_FULL_PATH)
        )
