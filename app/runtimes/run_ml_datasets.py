import sys
from pathlib import Path
from infra.spark.spark_session import SparkSessionFactory
from ml.datasets.ml_dataset_processor import MLDatasetProcessor
from ml.datasets.ml_split_processor import MLSplitProcessor
from ml.training.ml_training_processor import MLTrainingProcessor

# Environment configuration
ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXEC = sys.executable

def run_ml_workflow(spark):
    """
    Orchestrates the machine learning pipeline from data preparation to model training.
    Ensures a consistent flow of data between Spark-based processing and MLflow-tracked training.
    """
    
    # 1. Dataset Generation: Flattens Gold Delta tables into ML-ready formats
    print("\n🚀 Executing MLDatasetProcessor (Flattening & Cleaning)...")
    MLDatasetProcessor(spark).run()

    # 2. Data Splitting: Partitioning data by simulation_id to prevent leakage
    print("\n🚀 Executing MLSplitProcessor (Group-based Train/Test Split)...")
    MLSplitProcessor(spark).run()

    # 3. Model Training: Fitting the classifier and logging results to MLflow
    print("\n🚀 Executing MLTrainingProcessor (Model Fit & Experiment Tracking)...")
    MLTrainingProcessor(spark).run()

if __name__ == "__main__":
    """
    Main entry point for the ML pipeline. 
    Initializes a dedicated Spark session for machine learning data operations.
    """
    spark = SparkSessionFactory.create("ml-orchestration-pipeline")
    
    try:
        run_ml_workflow(spark)
        print("\n✅ ML PIPELINE COMPLETED: Models and datasets are ready.")
    except Exception as e:
        print(f"\n❌ ML PIPELINE FAILED: {str(e)}")
        sys.exit(1)