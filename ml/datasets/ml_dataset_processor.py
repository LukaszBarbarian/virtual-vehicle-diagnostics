# ml/datasets/ml_dataset_processor.py
from pyspark.sql import functions as F
from pyspark.sql import DataFrame
from pipelines.base.processor import BaseProcessor
from app.app_config import AppConfig
from ml.datasets.feature_config import FEATURE_COLUMNS, TARGET_COLUMN, META_COLUMNS

class MLDatasetProcessor(BaseProcessor):
    """
    Final data preparation stage for Machine Learning. 
    Filters data, ensures target availability, and exports to a flat Parquet format.
    """

    def read(self) -> DataFrame:
        """
        Reads the curated feature set from the Gold Delta table.
        """
        return (
            self.spark.read
            .format("delta")
            .load(AppConfig.GOLD_FEATURES_PATH)
        )

    def transform(self, df: DataFrame) -> DataFrame:
        """
        Removes records where the target label is null. 
        Note: Target may be null at the end of a simulation due to the look-ahead window.
        """
        return df.filter(F.col(TARGET_COLUMN).isNotNull())

    def process(self, df: DataFrame) -> DataFrame:
        """
        Prunes the dataset to include only metadata, input features, and the target label.
        """
        selected_cols = META_COLUMNS + FEATURE_COLUMNS + [TARGET_COLUMN]
        return df.select(*selected_cols)

    def write(self, df: DataFrame):
        """
        Persists the finalized dataset as a Parquet file for high-performance training consumption.
        """
        (
            df.write
            .format("parquet")
            .mode("overwrite")
            .save(AppConfig.ML_DATASET_FULL_PATH)
        )