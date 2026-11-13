import mlflow

from app.app_config import AppConfig


def configure_mlflow() -> None:
    """
    Points MLflow at the project's tracking store and experiment.
    Artifacts are stored under <project>/mlruns regardless of the working directory.
    """
    mlflow.set_tracking_uri(AppConfig.MLFLOW_TRACKING_URI)
    if mlflow.get_experiment_by_name(AppConfig.MLFLOW_EXPERIMENT) is None:
        mlflow.create_experiment(
            AppConfig.MLFLOW_EXPERIMENT,
            artifact_location=AppConfig.MLFLOW_ARTIFACT_DIR.as_uri(),
        )
    mlflow.set_experiment(AppConfig.MLFLOW_EXPERIMENT)
