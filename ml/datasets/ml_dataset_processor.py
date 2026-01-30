# ml/datasets/ml_dataset_processor.py
from pyspark.sql import functions as F
from pipelines.base.processor import BaseProcessor
from app.app_config import AppConfig
from ml.datasets.feature_config import FEATURE_COLUMNS, TARGET_COLUMN, META_COLUMNS

class MLDatasetProcessor(BaseProcessor):
    """
    Prepares the final flat dataset for ML. 
    Filters out records with missing target values.
    """

    def read(self):
        return (
            self.spark.read
            .format("delta")
            .load(AppConfig.GOLD_FEATURES_PATH) # Zmieniona ścieżka na Gold
        )

    def transform(self, df):
        # We ensure target column is not null (due to the 30s look-ahead window)
        return df.filter(F.col(TARGET_COLUMN).isNotNull())

    def process(self, df):
        """
        Selects only relevant columns for the ML model.
        """
        selected_cols = META_COLUMNS + FEATURE_COLUMNS + [TARGET_COLUMN]
        return df.select(*selected_cols)

    def write(self, df):
        """Saves the flat dataset as Parquet for efficient ML training."""
        (
            df.write
            .format("parquet")
            .mode("overwrite")
            .save(AppConfig.ML_DATASET_FULL_PATH)
        )