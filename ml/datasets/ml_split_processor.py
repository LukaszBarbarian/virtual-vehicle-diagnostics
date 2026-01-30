from pyspark.sql import functions as F
from pyspark.sql import DataFrame
from typing import Tuple
from pipelines.base.processor import BaseProcessor
from app.app_config import AppConfig

class MLSplitProcessor(BaseProcessor):
    """
    Handles the splitting of the full ML dataset into training and testing sets.
    Uses a group-based split strategy (by simulation_id) to prevent data leakage.
    """

    TRAIN_RATIO = 0.8

    def read(self) -> DataFrame:
        """
        Reads the full, processed ML dataset from Parquet storage.
        """
        return (
            self.spark.read
            .format("parquet")
            .load(AppConfig.ML_DATASET_FULL_PATH)
        )

    def transform(self, df: DataFrame) -> DataFrame:
        """
        Pass-through transformation for the splitting stage.
        """
        return df

    def process(self, df: DataFrame) -> Tuple[DataFrame, DataFrame]:
        """
        Executes a group split logic. Identifies unique simulations and assigns 
        them to either training or testing sets based on the TRAIN_RATIO.
        """
        # Collect unique simulation IDs to the driver for deterministic splitting
        simulation_ids = [
            r.simulation_id
            for r in (
                df.select("simulation_id")
                .distinct()
                .orderBy("simulation_id")
                .collect()
            )
        ]
        
        num_sims = len(simulation_ids)
        
        # Guard against empty or insufficient datasets
        if num_sims < 2:
            print("WARNING: Insufficient unique simulations for a proper split. Using same set for both.")
            train_ids = set(simulation_ids)
            test_ids = set(simulation_ids)
        else:
            # Calculate split index ensuring at least one simulation per set
            split_idx = max(1, int(num_sims * self.TRAIN_RATIO))
            train_ids = set(simulation_ids[:split_idx])
            test_ids = set(simulation_ids[split_idx:])

        # Partition the Spark DataFrame based on the selected IDs
        train_df = df.filter(F.col("simulation_id").isin(train_ids))
        test_df = df.filter(F.col("simulation_id").isin(test_ids))

        return train_df, test_df

    def write(self, dfs: Tuple[DataFrame, DataFrame]):
        """
        Persists the resulting train and test splits into separate Parquet files.
        """
        train_df, test_df = dfs

        (
            train_df
            .write
            .mode("overwrite")
            .parquet(AppConfig.ML_DATASET_TRAIN_PATH)
        )

        (
            test_df
            .write
            .mode("overwrite")
            .parquet(AppConfig.ML_DATASET_TEST_PATH)
        )