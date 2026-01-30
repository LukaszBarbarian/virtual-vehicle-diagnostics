import sys
from pathlib import Path
from infra.spark.spark_session import SparkSessionFactory
from pipelines.processor.silver_processor import SilverProcessor
from pipelines.processor.gold_processor import GoldProcessor

# Setup environment paths
ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXEC = sys.executable

def run_batch_pipeline(spark):
    """
    Executes the batch processing sequence for the Medallion architecture.
    Orchestrates the transition from structured Silver data to curated Gold features.
    """
    
    # 1. Silver Processing: Validate and flatten raw data
    print("\n🚀 Starting SilverProcessor (Validation & Flattening)...")
    SilverProcessor(spark).run()

    # 2. Gold Processing: Feature engineering and ML labeling
    print("\n🚀 Starting GoldProcessor (Feature Engineering & Labeling)...")
    GoldProcessor(spark).run()

if __name__ == "__main__":
    """
    Entry point for the data pipeline execution.
    Initializes the Spark session and triggers the batch workflow.
    """
    # Create a dedicated Spark session for batch processing
    spark = SparkSessionFactory.create("medallion-pipeline-orchestrator")
    
    try:
        run_batch_pipeline(spark)
        print("\n✅ DATA PIPELINE EXECUTION FINISHED SUCCESSFULLY")
    except Exception as e:
        print(f"\n❌ PIPELINE FAILED: {str(e)}")
        sys.exit(1)