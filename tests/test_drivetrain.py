"""Driving physics: shift map per driver profile, rev limiter, plausible performance."""
import statistics

import pytest

from app.app_config import AppConfig
from conftest import build_simulation, run_simulation
from simulator.core.loader.driver_profile import DriverProfileLoader


def drive(style: str, pedal: float, car: str = "ford_focus", ticks: int = 900) -> list:
    sim = build_simulation(AppConfig.MAIN_PROFILES_PATH / "cars" / f"{car}.yaml")
    sim.driver.apply_config(DriverProfileLoader.load(AppConfig.MAIN_PROFILES_PATH / "drivers" / f"{style}.yaml"))
    return run_simulation(sim, lambda t: pedal, ticks)


def upshift_rpms(states: list) -> list:
    rpms, prev_gear, prev_rpm = [], None, 0.0
    for s in states:
        gear, rpm = s["modules"]["gearbox"]["current_gear"], s["modules"]["engine"]["engine_rpm"]
        if prev_gear is not None and gear > prev_gear:
            rpms.append(prev_rpm)
        prev_gear, prev_rpm = gear, rpm
    return rpms


def cruising_rpm(states: list) -> float:
    return statistics.mean(s["modules"]["engine"]["engine_rpm"] for s in states[300:])


def test_eco_changes_up_earlier_than_normal_and_sport():
    eco, normal, sport = (upshift_rpms(drive(style, 0.3))[1:] for style in ("eco", "normal", "sport"))
    assert statistics.mean(eco) < statistics.mean(normal) < statistics.mean(sport)
    assert statistics.mean(eco) < 3000  # light pedal in eco: change up below 3 000 rpm


def test_profiles_keep_different_revs_at_the_same_pedal():
    eco, normal, sport = (cruising_rpm(drive(style, 0.3)) for style in ("eco", "normal", "sport"))
    assert eco < normal < sport


def test_full_pedal_holds_gears_longer_than_light_pedal():
    assert statistics.mean(upshift_rpms(drive("normal", 1.0))) > statistics.mean(upshift_rpms(drive("normal", 0.3))) + 1500


@pytest.mark.parametrize("car,max_rpm,top_speed", [("ford_focus", 6500, (190, 240)), ("lambo", 9000, (280, 340))])
def test_rev_limiter_caps_rpm_and_top_speed(car, max_rpm, top_speed):
    states = drive("sport", 1.0, car, ticks=2400)
    assert max(s["modules"]["engine"]["engine_rpm"] for s in states) <= max_rpm
    final_speed = states[-1]["modules"]["vehicle"]["speed_kmh"]
    assert top_speed[0] <= final_speed <= top_speed[1]


@pytest.mark.parametrize("car,seconds", [("ford_focus", (6.5, 10.0)), ("lambo", (2.5, 4.0))])
def test_zero_to_hundred_is_plausible(car, seconds):
    states = drive("sport", 1.0, car, ticks=200)
    t100 = next(s["time"] for s in states if s["modules"]["vehicle"]["speed_kmh"] >= 100)
    assert seconds[0] <= t100 <= seconds[1]
