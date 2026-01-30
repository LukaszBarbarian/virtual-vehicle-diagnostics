from pyspark.sql import functions as F

from pipelines.base.processor import BaseProcessor
from app.app_config import AppConfig


class MLSplitProcessor(BaseProcessor):
    """
    ML dataset split:
    - Spark for read/write
    - Python (driver-only) for split logic
    """

    TRAIN_RATIO = 0.8

    # --------------------------------------------------
    # READ (Spark)
    # --------------------------------------------------
    def read(self):
        return (
            self.spark.read
            .format("parquet")
            .load(AppConfig.ML_DATASET_FULL_PATH)
        )

    # --------------------------------------------------
    # TRANSFORM (NO-OP)
    # --------------------------------------------------
    def transform(self, df):
        return df

    # --------------------------------------------------
    # PROCESS (HYBRID)
    # --------------------------------------------------
    def process(self, df):
        # Pobieramy unikalne ID symulacji
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
        print(f"DEBUG: Found {num_sims} unique simulations.")

        if num_sims < 2:
            print("WARNING: Only 1 simulation found. Using it for both Train and Test to avoid crash!")
            train_ids = set(simulation_ids)
            test_ids = set(simulation_ids)
        else:
            # Gwarantujemy min. 1 symulację dla treningu
            split_idx = max(1, int(num_sims * self.TRAIN_RATIO))
            train_ids = set(simulation_ids[:split_idx])
            test_ids = set(simulation_ids[split_idx:])

        print(f"DEBUG: Training on {len(train_ids)} sims, Testing on {len(test_ids)} sims")

        train_df = df.filter(F.col("simulation_id").isin(train_ids))
        test_df = df.filter(F.col("simulation_id").isin(test_ids))

        return train_df, test_df

    # --------------------------------------------------
    # WRITE (Spark)
    # --------------------------------------------------
    def write(self, dfs):
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
