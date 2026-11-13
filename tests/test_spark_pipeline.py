"""
Spark tests: Bronze JSON -> Silver -> Gold on a simulated session, and parity between
the Gold training features and the live inference features. Skipped without pyspark/Java.
"""
import json
import os
import shutil
import sys

import pytest

pytest.importorskip("pyspark")
pytest.importorskip("delta")

from ml.datasets.feature_config import FEATURE_COLUMNS, META_COLUMNS, TARGET_COLUMN, WINDOW_LAG, WINDOW_ROWS  # noqa: E402
from ml.inference.inference_processor import compute_window_features  # noqa: E402
from pipelines.processor.gold_processor import GoldProcessor  # noqa: E402
from pipelines.processor.silver_processor import SilverProcessor  # noqa: E402
from streaming.events.simulation import RawSimulationStateEvent  # noqa: E402


@pytest.fixture(scope="module")
def spark():
    if shutil.which("java") is None:
        pytest.skip("Java is required for Spark")
    # Python workers must use this interpreter (on Windows there is no "python3" on PATH)
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    builder = (
        SparkSession.builder.master("local[2]").appName("vvd-tests")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
    )
    session = configure_spark_with_delta_pip(builder).getOrCreate()
    yield session
    session.stop()


def read_bronze(spark, directory, events):
    """Writes events in the Bronze JSON-lines format and reads them back as SilverProcessor does."""
    path = directory / "part-00000.json"
    with open(path, "w", encoding="utf-8") as f:
        for i, event in enumerate(events):
            f.write(json.dumps({"partition": 0, "offset": i, "raw_event": json.dumps(event)}) + "\n")
    return spark.read.format("json").load(directory.as_uri())


@pytest.fixture(scope="module")
def session_states():
    from conftest import build_simulation, run_simulation
    return run_simulation(build_simulation(), lambda t: 0.9 if (t // 150) % 2 else 0.3, ticks=600)


@pytest.fixture(scope="module")
def silver_and_gold(spark, session_states, tmp_path_factory):
    # Bronze files look exactly like the Kafka sink output: the event JSON in raw_event
    events = [RawSimulationStateEvent(raw_state_dict=s).to_dict() for s in session_states]
    bronze = read_bronze(spark, tmp_path_factory.mktemp("bronze"), events + events[:5])  # 5 duplicated ticks

    silver_processor = SilverProcessor(spark)
    parsed = silver_processor._apply_quality_checks(
        silver_processor._project_silver(silver_processor._parse_raw_event(bronze))
    )
    silver, quarantine = silver_processor._split_valid_quarantine(parsed)
    gold = GoldProcessor(spark).transform(silver).select(*META_COLUMNS, *FEATURE_COLUMNS, TARGET_COLUMN)
    return silver.toPandas(), quarantine.count(), gold.toPandas()


def test_silver_flattens_and_deduplicates(silver_and_gold, session_states):
    silver, quarantined, _ = silver_and_gold

    assert quarantined == 0
    assert len(silver) == len(session_states)
    assert silver[["simulation_id", "step"]].duplicated().sum() == 0
    assert silver["engine_rpm"].notna().all()


def test_gold_labels_both_classes(silver_and_gold):
    _, _, gold = silver_and_gold

    assert set(gold[TARGET_COLUMN]) == {"AGGRESSIVE", "NORMAL"}
    # Only ticks with a full 10-second history are kept
    assert gold["step"].min() == WINDOW_LAG
    assert gold[FEATURE_COLUMNS].notna().all().all()


def test_gold_features_equal_live_inference_features(silver_and_gold):
    silver, _, gold = silver_and_gold
    silver = silver.sort_values("step").reset_index(drop=True)

    for step in [WINDOW_LAG, WINDOW_LAG + 77, int(gold["step"].max())]:
        window = silver[(silver["step"] > step - WINDOW_ROWS) & (silver["step"] <= step)]
        live = compute_window_features(window)
        trained = gold[gold["step"] == step].iloc[0]
        for column in FEATURE_COLUMNS:
            assert trained[column] == pytest.approx(live[column], rel=1e-9, abs=1e-9), (step, column)


def test_silver_rejects_out_of_range_ticks(spark, session_states, tmp_path):
    bad = json.loads(json.dumps(RawSimulationStateEvent(raw_state_dict=session_states[0]).to_dict()))
    bad["payload"]["modules"]["engine"]["engine_rpm"] = 25000
    processor = SilverProcessor(spark)
    df = read_bronze(spark, tmp_path, [bad])
    checked = processor._apply_quality_checks(processor._project_silver(processor._parse_raw_event(df)))
    valid, quarantine = processor._split_valid_quarantine(checked)

    assert valid.count() == 0
    assert quarantine.count() == 1
