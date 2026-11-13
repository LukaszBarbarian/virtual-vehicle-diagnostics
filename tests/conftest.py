import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.app_config import AppConfig  # noqa: E402
from ml.datasets.feature_config import SIM_DT  # noqa: E402
from simulator.core.loader.car_profile import CarProfileLoader  # noqa: E402
from simulator.core.loader.driver_profile import DriverProfileLoader  # noqa: E402
from simulator.core.loader.environment_profile import EnvironmentLoader  # noqa: E402
from simulator.core.loader.wear_profile import WearProfileLoader  # noqa: E402
from simulator.core.simulation.simulation import Simulation  # noqa: E402


def build_simulation(car_profile=AppConfig.DEFAULT_CAR_PROFILE) -> Simulation:
    return Simulation(
        CarProfileLoader.load(car_profile),
        DriverProfileLoader.load(AppConfig.DEFAULT_DRIVER_PROFILE),
        WearProfileLoader.load(AppConfig.WEAR_PROFILE),
        EnvironmentLoader.load(AppConfig.ENVIRONMENT_PROFILE),
    )


def run_simulation(sim: Simulation, pedal_schedule, ticks: int) -> list:
    """Steps the simulation headless (no Kafka) and returns the published states as dicts."""
    states = []
    sim.state_bus.subscribe(lambda raw: states.append(raw.to_dict()))
    for tick in range(ticks):
        sim.driver.set_external_pedal(pedal_schedule(tick))
        sim.step(SIM_DT)
    return states


@pytest.fixture
def simulated_session():
    """About 60 seconds of driving with alternating calm and hard throttle."""
    sim = build_simulation()
    states = run_simulation(sim, lambda t: 0.9 if (t // 150) % 2 else 0.3, ticks=600)
    return sim, states
