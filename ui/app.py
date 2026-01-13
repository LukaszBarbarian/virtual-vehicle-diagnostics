# ui/app.py
from pathlib import Path
import sys
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from enum import Enum

# =====================================================
# PATH FIX
# =====================================================
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# =====================================================
# DOMAIN IMPORTS
# =====================================================
from simulator.core.simulation.scenarios.steady_cruise_scenario import (
    SteadyCruiseScenario
)
from app.runtime import ApplicationRuntime
from ui.enums.state import SimState
from widgets import throttle_slider
from gauges import rpm_gauge, speed_gauge
from charts import rpm_gear_timeseries

# =====================================================
# CONTROL MODE
# =====================================================
class ControlMode(Enum):
    MANUAL = 0
    SCENARIO = 1

# =====================================================
# HARD SESSION INIT (CRITICAL)
# =====================================================
if "initialized" not in st.session_state:
    st.session_state.clear()
    st.session_state.initialized = True
    st.session_state.sim_state = SimState.OFF
    st.session_state.control_mode = ControlMode.MANUAL
    st.session_state.throttle = 0.0
    st.session_state.app_runtime = None
    st.session_state.dashboard_handler = None
    st.session_state.driver_publisher = None
    st.session_state.car_meta = None
    st.session_state.max_rpm = 6000
    st.session_state.redline = 5000

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(layout="wide")
st.title("🚗 Vehicle Control Panel")

# 🔑 dashboard refresh ONLY when running
if st.session_state.sim_state == SimState.RUNNING:
    st_autorefresh(interval=300, key="dashboard_refresh")

# =====================================================
# HELPERS
# =====================================================
def parse_dashboard_state(state: dict) -> dict:
    engine = state["modules"]["engine"]
    vehicle = state["modules"]["vehicle"]
    thermals = state["modules"]["thermals"]
    gearbox = state["modules"]["gearbox"]

    rpm = engine.get("engine_rpm", 0.0)
    speed = vehicle.get("speed_kmh", 0.0)
    temp = thermals.get("coolant_temp_c", 20.0)

    gear = gearbox.get("current_gear", 0)
    shifting = gearbox.get("shifting", False)

    fuel_lph = engine.get("fuel_rate_lph", 0.0)
    fuel_l_per_100km = engine.get("fuel_l_per_100km")

    fuel = (
        f"{fuel_l_per_100km:.1f} L/100km"
        if speed > 5 and fuel_l_per_100km is not None
        else f"{fuel_lph:.2f} L/h"
    )

    gear_label = f"D{gear}" if gear > 0 else "N"
    if shifting:
        gear_label += "…"

    return {
        "rpm": rpm,
        "speed": speed,
        "temp": temp,
        "gear": gear_label,
        "fuel": fuel,
    }


def extract_car_meta(runtime) -> dict:
    spec = runtime.car_spec
    return {
        "name": spec.name,
        "engine": {
            "max_rpm": spec.engine.max_rpm,
            "max_power_kw": spec.engine.max_power_kw,
        },
        "vehicle": {
            "mass_kg": spec.vehicle.mass_kg
        }
    }


def render_car_header():
    car = st.session_state.car_meta
    if not car:
        st.markdown("### 🚗 Vehicle simulation")
        return

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    c1.markdown(f"## 🚗 {car['name']}")
    c2.metric("Max RPM", car["engine"]["max_rpm"])
    c3.metric("Power", f"{car['engine']['max_power_kw']} kW")
    c4.metric("Mass", f"{car['vehicle']['mass_kg']} kg")
    st.divider()


def on_control_mode_change():
    # SCENARIO → start scenario + play (EVENT)
    if (
        st.session_state.sim_state == SimState.READY
        and st.session_state.control_mode.value == ControlMode.SCENARIO.value
    ):
        st.session_state.app_runtime.start_scenario_sequence(
            [SteadyCruiseScenario()]
        )
        st.session_state.app_runtime.play()
        st.session_state.sim_state = SimState.RUNNING



# =====================================================
# ENGINE CONTROL
# =====================================================
def start_engine():
    app_rt = ApplicationRuntime("localhost:9092").start()

    st.session_state.app_runtime = app_rt
    st.session_state.dashboard_handler = app_rt.dashboard_handler
    st.session_state.driver_publisher = app_rt.driver_publisher
    st.session_state.car_meta = extract_car_meta(app_rt.simulation)

    engine = app_rt.simulation.sim.car.engine
    st.session_state.max_rpm = engine.max_rpm
    st.session_state.redline = engine.max_rpm * engine.limiter_start_ratio

    if st.session_state.driver_publisher:
        st.session_state.driver_publisher.set_throttle(0.0)

    st.session_state.sim_state = SimState.READY


def stop_engine():
    if st.session_state.app_runtime:
        st.session_state.app_runtime.stop()

    st.session_state.sim_state = SimState.OFF
    st.session_state.throttle = 0.0
    st.session_state.app_runtime = None
    st.session_state.dashboard_handler = None
    st.session_state.driver_publisher = None
    st.session_state.car_meta = None

# =====================================================
# LAYOUT
# =====================================================
control_col, dash_col = st.columns([1, 3])

# =====================================================
# CONTROL PANEL
# =====================================================
with control_col:
    st.subheader("Controls")

    is_off = st.session_state.sim_state == SimState.OFF
    label = "START ENGINE" if is_off else "STOP ENGINE"

    if st.button(label, use_container_width=True):
        start_engine() if is_off else stop_engine()

    st.divider()

    st.radio(
        "Control mode",
        [ControlMode.MANUAL, ControlMode.SCENARIO],
        format_func=lambda x: x.name,
        key="control_mode",
        horizontal=True,
        label_visibility="collapsed",
        on_change=on_control_mode_change
    )

    
    st.divider()

    throttle_disabled = (
        st.session_state.sim_state == SimState.OFF
        or st.session_state.control_mode.value == ControlMode.SCENARIO.value
    )

    new_throttle = throttle_slider(
        st.session_state.throttle,
        disabled=throttle_disabled
    )

    if (
        st.session_state.sim_state == SimState.READY
        and st.session_state.control_mode.value == ControlMode.MANUAL.value
        and new_throttle > 0.0
    ):
        st.session_state.app_runtime.play()
        st.session_state.sim_state = SimState.RUNNING

    if (
        st.session_state.sim_state == SimState.RUNNING
        and st.session_state.control_mode.value == ControlMode.MANUAL.value
    ):
        st.session_state.driver_publisher.set_throttle(new_throttle)

    st.session_state.throttle = new_throttle

    st.metric("Throttle", f"{int(new_throttle * 100)} %")
    st.caption(f"STATE: {st.session_state.sim_state.value}")
    st.caption(f"MODE: {st.session_state.control_mode.value}")

# =====================================================
# DASHBOARD
# =====================================================
with dash_col:
    render_car_header()

    handler = st.session_state.dashboard_handler
    raw_state = handler.get_latest_state() if handler else None
    history = handler.get_history() if handler else []

    data = (
        parse_dashboard_state(raw_state)
        if raw_state else
        {"rpm": 0, "speed": 0, "temp": 20, "gear": "N", "fuel": "0.0 L/h"}
    )

    g1, g2, g3, g4, g5 = st.columns(5)
    g1.plotly_chart(
        rpm_gauge(data["rpm"], st.session_state.max_rpm, st.session_state.redline),
        use_container_width=True
    )
    g2.plotly_chart(speed_gauge(data["speed"], 220), use_container_width=True)
    g3.metric("🌡️ Coolant", f"{data['temp']:.1f} °C")
    g4.metric("⚙️ Gear", data["gear"])
    g5.metric("⛽ Fuel", data["fuel"])

    st.divider()
    st.plotly_chart(rpm_gear_timeseries(history), use_container_width=True)
