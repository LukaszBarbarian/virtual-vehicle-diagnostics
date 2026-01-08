# ui/widgets.py
import streamlit as st

def start_stop_button(is_on: bool) -> bool:
    label = "🟢 START ENGINE" if not is_on else "🔴 STOP ENGINE"
    return st.button(label, use_container_width=True)

def throttle_slider(value: float) -> float:
    return st.slider(
        "Throttle",
        min_value=0.0,
        max_value=1.0,
        value=value,
        step=0.01
    )
