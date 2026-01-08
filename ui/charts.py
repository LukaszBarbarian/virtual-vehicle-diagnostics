import plotly.graph_objects as go


def rpm_gear_timeseries(history):
    if not history:
        return go.Figure()

    t = [p["t"] for p in history]
    rpm = [p["rpm"] for p in history]
    gear = [p["gear"] for p in history]
    speed = [p["speed_kmh"] for p in history]  # <-- prędkość (km/h)

    fig = go.Figure()

    # === RPM ===
    fig.add_trace(go.Scatter(
        x=t,
        y=rpm,
        mode="lines",
        name="RPM",
        line=dict(color="#e74c3c", width=2),
        yaxis="y1"
    ))

    # === GEAR (step) ===
    fig.add_trace(go.Scatter(
        x=t,
        y=gear,
        mode="lines",
        name="Gear",
        line=dict(color="#3498db", width=2, shape="hv"),
        yaxis="y2"
    ))

    # === SPEED ===
    fig.add_trace(go.Scatter(
        x=t,
        y=speed,
        mode="lines",
        name="Speed (km/h)",
        line=dict(color="#2ecc71", width=2, dash="dot"),
        yaxis="y3"
    ))

    fig.update_layout(
        title="🌀 RPM • ⚙️ Gear • 🚗 Speed over Time",
        xaxis=dict(title="Time"),

        # RPM
        yaxis=dict(
            title="RPM",
            side="left",
            showgrid=False
        ),

        # Gear
        yaxis2=dict(
            title="Gear",
            overlaying="y",
            side="right",
            range=[0, max(gear) + 1],
            showgrid=False
        ),

        # Speed (second right axis, shifted)
        yaxis3=dict(
            title="Speed (km/h)",
            overlaying="y",
            side="right",
            position=0.92,
            showgrid=False
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),

        height=320,
        margin=dict(t=60, b=30, l=50, r=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white")
    )

    return fig
