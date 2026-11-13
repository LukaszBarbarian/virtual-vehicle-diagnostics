from pathlib import Path

import pytest

from app.app_config import AppConfig
from conftest import build_simulation, run_simulation


@pytest.mark.parametrize("car_profile", sorted((AppConfig.MAIN_PROFILES_PATH / "cars").glob("*.yaml")), ids=lambda p: Path(p).stem)
def test_every_car_profile_drives(car_profile):
    sim = build_simulation(car_profile)
    states = run_simulation(sim, lambda t: 0.6, ticks=300)

    assert states, "the simulation published no ticks"
    final = states[-1]["modules"]
    assert final["vehicle"]["speed_kmh"] > 20
    assert final["gearbox"]["current_gear"] >= 2


def test_ticks_are_consecutive_snapshots(simulated_session):
    sim, states = simulated_session

    steps = [s["step"] for s in states]
    assert steps == list(range(len(states)))
    assert {s["simulation_id"] for s in states} == {sim.simulation_id}

    # Snapshots must be copies: earlier ticks keep their own values
    speeds = [s["modules"]["vehicle"]["speed_kmh"] for s in states]
    assert len(set(speeds)) > 10


def test_engine_wear_never_decreases(simulated_session):
    _, states = simulated_session
    wear = [s["modules"]["wear"]["engine_wear"] for s in states]

    assert all(later >= earlier for earlier, later in zip(wear, wear[1:]))
    assert wear[-1] > wear[0]


def test_telemetry_stays_within_silver_quality_ranges(simulated_session):
    _, states = simulated_session
    for s in states:
        m = s["modules"]
        assert 0 <= m["engine"]["engine_rpm"] <= 10000
        assert 0 <= m["vehicle"]["speed_kmh"] <= 500
        assert 0 <= m["driver"]["throttle"] <= 1.1
        assert -50 <= m["thermals"]["coolant_temp_c"] <= 250
