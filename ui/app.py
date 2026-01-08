# ui/app.py
from pathlib import Path
import sys
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ===== PATH FIX =====
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simulator.runtime import SimulationRuntime
from streaming.producers.driver_command import DriverCommandPublisher
from streaming.kafka_service import KafkaService
from streaming.consumers.runner import KafkaConsumerRunner
from streaming.consumers.dashboard import DashboardStateHandler

from state import SimState
from widgets import throttle_slider
from gauges import rpm_gauge, speed_gauge
from charts import rpm_gear_timeseries


# =====================================================
# CONFIG
# =====================================================
st.set_page_config(layout="wide")
st.title("🚗 Vehicle Control Panel")

# UI refresh ONLY (no logic here)
st_autorefresh(interval=200, key="dashboard_refresh")


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

    if speed > 5 and fuel_l_per_100km is not None:
        fuel = f"{fuel_l_per_100km:.1f} L/100km"
    else:
        fuel = f"{fuel_lph:.2f} L/h"

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


# =====================================================
# CSS
# =====================================================
st.markdown(
    """
    <style>
    .start-btn button {
        height: 80px;
        font-size: 22px;
        border-radius: 50px;
        background: radial-gradient(circle at 30% 30%, #2ecc71, #145a32);
        color: white;
    }
    .stop-btn button {
        height: 80px;
        font-size: 22px;
        border-radius: 50px;
        background: radial-gradient(circle at 30% 30%, #e74c3c, #922b21);
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# SESSION STATE INIT
# =====================================================
if "sim_state" not in st.session_state:
    st.session_state.sim_state = SimState.OFF
    st.session_state.throttle = 0.0

    st.session_state.runtime = None
    st.session_state.kafka_consumer = None
    st.session_state.dashboard_handler = None
    st.session_state.driver_publisher = None

    st.session_state.max_rpm = 6000
    st.session_state.redline = 5000


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
    btn_class = "start-btn" if is_off else "stop-btn"

    st.markdown(f'<div class="{btn_class}">', unsafe_allow_html=True)
    clicked = st.button(label)
    st.markdown("</div>", unsafe_allow_html=True)

    if clicked:
        if st.session_state.sim_state == SimState.OFF:
            # ---- START ----
            runtime = SimulationRuntime().bootstrap()
            st.session_state.runtime = runtime

            kafka = KafkaService("localhost:9092")

            handler = DashboardStateHandler()
            consumer = KafkaConsumerRunner(
                kafka=kafka,
                topic="simulation.raw",
                group_id="dashboard",
                handler=handler
            )
            consumer.start()

            st.session_state.kafka_consumer = consumer
            st.session_state.dashboard_handler = handler
            st.session_state.driver_publisher = DriverCommandPublisher(kafka)

            st.session_state.max_rpm = runtime.sim.car.engine.max_rpm
            st.session_state.redline = (
                runtime.sim.car.engine.max_rpm
                * runtime.sim.car.engine.limiter_start_ratio
            )

            st.session_state.sim_state = SimState.READY

        else:
            # ---- STOP ----
            if st.session_state.runtime:
                st.session_state.runtime.shutdown()

            if st.session_state.kafka_consumer:
                st.session_state.kafka_consumer.stop()

            st.session_state.runtime = None
            st.session_state.kafka_consumer = None
            st.session_state.dashboard_handler = None
            st.session_state.driver_publisher = None

            st.session_state.throttle = 0.0
            st.session_state.sim_state = SimState.OFF

    st.divider()

    # ---------- THROTTLE ----------
    if st.session_state.sim_state != SimState.OFF:
        new_throttle = throttle_slider(st.session_state.throttle)

        if (
            new_throttle != st.session_state.throttle
            and st.session_state.driver_publisher
        ):
            st.session_state.driver_publisher.set_throttle(new_throttle)

        st.session_state.throttle = new_throttle

        if (
            new_throttle > 0
            and st.session_state.sim_state == SimState.READY
        ):
            st.session_state.runtime.start_engine(dt=0.1)
            st.session_state.sim_state = SimState.RUNNING

        st.metric("Throttle", f"{int(new_throttle * 100)} %")

    st.caption(f"STATE: {st.session_state.sim_state}")


# =====================================================
# DASHBOARD
# =====================================================
with dash_col:
    st.subheader("Dashboard")

    if st.session_state.dashboard_handler:
        raw_state = st.session_state.dashboard_handler.get_latest_state()
        history = st.session_state.dashboard_handler.get_history()
    else:
        raw_state = None
        history = []

    if raw_state:
        data = parse_dashboard_state(raw_state)
    else:
        data = {
            "rpm": 0.0,
            "speed": 0.0,
            "temp": 20.0,
            "gear": "N",
            "fuel": "0.0 L/h",
        }

    g1, g2, g3, g4, g5 = st.columns(5)

    with g1:
        st.plotly_chart(
            rpm_gauge(
                data["rpm"],
                st.session_state.max_rpm,
                st.session_state.redline
            ),
            use_container_width=True
        )

    with g2:
        st.plotly_chart(
            speed_gauge(data["speed"], 220),
            use_container_width=True
        )

    with g3:
        st.metric("🌡️ Coolant", f'{data["temp"]:.1f} °C')

    with g4:
        st.metric("⚙️ Gear", data["gear"])

    with g5:
        st.metric("⛽ Fuel", data["fuel"])

    st.divider()

    st.plotly_chart(
        rpm_gear_timeseries(history),
        use_container_width=True
    )
