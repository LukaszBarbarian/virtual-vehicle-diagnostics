# ui/gauges.py
import plotly.graph_objects as go

def rpm_gauge(rpm, max_rpm, redline):
    return go.Figure(go.Indicator(
        mode="gauge+number",
        value=rpm,
        number={"suffix": " RPM"},
        gauge={
            "axis": {
                "range": [0, max_rpm],
                "dtick": 1000   # 🔥 KLUCZ
            },
            "bar": {"color": "red"},
            "steps": [
                {"range": [0, redline], "color": "#2ecc71"},
                {"range": [redline, max_rpm], "color": "#e74c3c"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "value": redline
            }
        }
    ))


def speed_gauge(speed, max_speed):
    return go.Figure(go.Indicator(
        mode="gauge+number",
        value=speed,
        number={"suffix": " km/h"},
        gauge={
            "axis": {"range": [0, max_speed]},
            "bar": {"color": "#3498db"},
            "steps": [
                {"range": [0, max_speed * 0.7], "color": "#bdc3c7"},
                {"range": [max_speed * 0.7, max_speed], "color": "#2980b9"}
            ]
        }
    ))
