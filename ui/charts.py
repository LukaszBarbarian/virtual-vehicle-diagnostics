import plotly.graph_objects as go


def rpm_gear_timeseries(history, car_meta: dict | None = None):
    if not history:
        return go.Figure()

    t = [p["t"] for p in history]
    rpm = [p["rpm"] for p in history]
    gear = [p["gear"] for p in history]
    speed = [p["speed_kmh"] for p in history]

    car_name = car_meta.get("name", "Unknown vehicle") if car_meta else "Vehicle"

    # --- tooltip metadata ---
    if car_meta:
        engine = car_meta.get("engine", {})
        vehicle = car_meta.get("vehicle", {})

        hover_meta = (
            f"<b>{car_name}</b><br>"
            f"Max RPM: {engine.get('max_rpm', '?')}<br>"
            f"Power: {engine.get('max_power_kw', '?')} kW<br>"
            f"Torque: {engine.get('base_torque_nm', '?')} Nm<br>"
            f"Mass: {vehicle.get('mass_kg', '?')} kg"
        )
    else:
        hover_meta = car_name

    fig = go.Figure()

    # === RPM ===
    fig.add_trace(go.Scatter(
        x=t,
        y=rpm,
        mode="lines",
        name="RPM",
        line=dict(color="#e74c3c", width=2),
        yaxis="y1",
        hovertemplate=(
            hover_meta +
            "<br><br><b>RPM:</b> %{y:.0f}<br>"
            "<b>Time:</b> %{x:.1f}s<extra></extra>"
        )
    ))

    # === Gear ===
    fig.add_trace(go.Scatter(
        x=t,
        y=gear,
        mode="lines",
        name="Gear",
        line=dict(color="#3498db", width=2, shape="hv"),
        yaxis="y2",
        hovertemplate=(
            hover_meta +
            "<br><br><b>Gear:</b> %{y}<br>"
            "<b>Time:</b> %{x:.1f}s<extra></extra>"
        )
    ))

    # === Speed ===
    fig.add_trace(go.Scatter(
        x=t,
        y=speed,
        mode="lines",
        name="Speed (km/h)",
        line=dict(color="#2ecc71", width=2, dash="dot"),
        yaxis="y3",
        hovertemplate=(
            hover_meta +
            "<br><br><b>Speed:</b> %{y:.1f} km/h<br>"
            "<b>Time:</b> %{x:.1f}s<extra></extra>"
        )
    ))

    fig.update_layout(
        title=f"🚗 {car_name} — RPM • Gear • Speed",
        xaxis=dict(title="Time [s]"),

        yaxis=dict(
            title="RPM",
            side="left",
            showgrid=False
        ),
        yaxis2=dict(
            title="Gear",
            overlaying="y",
            side="right",
            range=[0, max(gear) + 1],
            showgrid=False
        ),
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

        height=340,
        margin=dict(t=70, b=30, l=50, r=70),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white")
    )

    return fig
