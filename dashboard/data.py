"""
Data access for the dashboard: reads the Delta tables of the lake with the `deltalake`
library (no Spark or Java needed) and the model + runs from MLflow.
"""
from urllib.parse import unquote, urlparse

import mlflow
import mlflow.sklearn
import pandas as pd
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from app.app_config import AppConfig, LakePaths
from ml.datasets.feature_config import FEATURE_COLUMNS, POSITIVE_CLASS, TARGET_COLUMN, split_simulation_ids
from ml.tracking.mlflow_setup import configure_mlflow


def _table_uri(uri: str) -> tuple[str, dict]:
    """Turns a lake URI into what deltalake expects: a local path, or abfss:// plus credentials."""
    if uri.startswith("file:"):
        path = unquote(urlparse(uri).path)
        # file:///C:/x -> /C:/x on Windows
        if len(path) > 2 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        return path, {}
    return uri, {
        "account_name": AppConfig.STORAGE_ACCOUNT or "",
        "account_key": AppConfig.STORAGE_ACCOUNT_KEY or "",
    }


def read_delta(uri: str, columns: list[str] | None = None) -> pd.DataFrame:
    """Reads a Delta table into pandas; an empty frame when the table does not exist yet."""
    path, options = _table_uri(uri)
    try:
        return DeltaTable(path, storage_options=options or None).to_pandas(columns=columns)
    except (TableNotFoundError, FileNotFoundError, OSError):
        return pd.DataFrame(columns=columns or [])


def load_silver() -> pd.DataFrame:
    df = read_delta(LakePaths.SILVER_STATE_PATH)
    if df.empty:
        return df
    if "driver_profile" not in df.columns:
        df["driver_profile"] = "unknown"
    df["driver_profile"] = df["driver_profile"].fillna("unknown")
    return df.sort_values(["simulation_id", "step"]).reset_index(drop=True)


def load_gold() -> pd.DataFrame:
    df = read_delta(LakePaths.GOLD_FEATURES_PATH)
    return df.sort_values(["simulation_id", "step"]).reset_index(drop=True) if not df.empty else df


def load_quality_metrics() -> pd.DataFrame:
    df = read_delta(LakePaths.DATA_QUALITY_METRICS_PATH)
    return df.sort_values("check_time").reset_index(drop=True) if not df.empty else df


def load_quarantine() -> pd.DataFrame:
    return read_delta(LakePaths.SILVER_QUARANTINE_PATH)


def session_summary(silver: pd.DataFrame, gold: pd.DataFrame) -> pd.DataFrame:
    """One row per session: profile, duration, speed, wear gained and share of aggressive windows."""
    if silver.empty:
        return pd.DataFrame()
    grouped = silver.groupby("simulation_id")
    summary = pd.DataFrame({
        "driver_profile": grouped["driver_profile"].first(),
        "duration_s": grouped["simulation_time"].max().round(0),
        "max_speed_kmh": grouped["speed_kmh"].max().round(0),
        "avg_rpm": grouped["engine_rpm"].mean().round(0),
        "max_oil_temp_c": grouped["oil_temp_c"].max().round(0),
        "wear_gained": grouped["engine_wear"].max() - grouped["engine_wear"].min(),
    })
    if not gold.empty:
        aggressive = gold.assign(is_aggr=gold[TARGET_COLUMN] == POSITIVE_CLASS).groupby("simulation_id")["is_aggr"].mean()
        summary["aggressive_share"] = aggressive
    train_ids, test_ids = split_simulation_ids(summary.index)
    summary["split"] = ["test" if sid in test_ids else "train" for sid in summary.index]
    return summary.reset_index()


# --------------------------------------------------------------------------- MLflow

class ModelInfo:
    """The registered model the cockpit serves, with its training run."""

    def __init__(self):
        configure_mlflow()
        self.client = mlflow.MlflowClient()
        versions = self.client.search_model_versions(f"name='{AppConfig.MODEL_NAME}'")
        if not versions:
            raise LookupError(f"No registered model '{AppConfig.MODEL_NAME}' in {AppConfig.MLFLOW_TRACKING_URI}")
        self.version = max(versions, key=lambda v: int(v.version))
        self.run = self.client.get_run(self.version.run_id)
        self.metrics = self.run.data.metrics
        self.model = mlflow.sklearn.load_model(f"models:/{AppConfig.MODEL_NAME}/{self.version.version}")

    def feature_importance(self) -> pd.Series:
        return pd.Series(dict(zip(FEATURE_COLUMNS, self.model.feature_importances_))).sort_values()

    def predict_proba(self, gold: pd.DataFrame) -> pd.Series:
        """P(AGGRESSIVE) for each Gold row."""
        if gold.empty:
            return pd.Series(dtype=float)
        aggressive_idx = list(self.model.classes_).index(POSITIVE_CLASS)
        return pd.Series(self.model.predict_proba(gold[FEATURE_COLUMNS])[:, aggressive_idx], index=gold.index)

    def run_history(self) -> pd.DataFrame:
        """Metrics of every training run in the experiment, oldest first."""
        runs = mlflow.search_runs(experiment_names=[AppConfig.MLFLOW_EXPERIMENT], order_by=["start_time ASC"])
        keep = [c for c in runs.columns if c.startswith("metrics.")] + ["run_id", "start_time"]
        runs = runs[keep].rename(columns=lambda c: c.replace("metrics.", ""))
        return runs.reset_index(drop=True)
