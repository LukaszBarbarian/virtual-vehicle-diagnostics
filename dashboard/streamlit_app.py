"""
Vehicle Diagnostics dashboard: sessions, session replay with live model output,
model quality and data quality, read straight from the lake and MLflow.

    streamlit run dashboard/streamlit_app.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from plotly.subplots import make_subplots  # noqa: E402

from app.app_config import AppConfig  # noqa: E402
from dashboard import data  # noqa: E402
from dashboard.theme import PROFILE_ORDER, profile_colors, template, tokens  # noqa: E402
from ml.datasets.feature_config import POSITIVE_CLASS, TARGET_COLUMN, split_simulation_ids  # noqa: E402

FEATURE_LABELS = {
    "oil_temp_c": "Oil temperature",
    "load_max_10s": "Max engine load (10 s)",
    "throttle_avg_10s": "Avg throttle (10 s)",
    "engine_load_avg_10s": "Avg engine load (10 s)",
    "rpm_range_10s": "RPM range (10 s)",
    "rpm_max_10s": "Max RPM (10 s)",
    "rpm_std_10s": "RPM std dev (10 s)",
    "rpm_avg_10s": "Avg RPM (10 s)",
    "power_factor": "Power factor (RPM × load)",
    "speed_kmh": "Speed",
    "current_gear": "Gear",
}

st.set_page_config(page_title="Vehicle Diagnostics", page_icon="🚗", layout="wide")


# --------------------------------------------------------------------------- data (cached)

@st.cache_data(ttl=60, show_spinner="Reading the lake...")
def get_lake():
    silver, gold = data.load_silver(), data.load_gold()
    return silver, gold, data.session_summary(silver, gold), data.load_quality_metrics(), data.load_quarantine()


@st.cache_resource(ttl=60, show_spinner="Loading the model from MLflow...")
def get_model():
    try:
        return data.ModelInfo(), None
    except Exception as e:  # no model trained yet, or MLflow unreachable
        return None, str(e)


@st.cache_data(ttl=60)
def get_predictions(_model, gold: pd.DataFrame, version: str) -> pd.Series:
    return _model.predict_proba(gold)


def theme_mode() -> str:
    try:
        return st.context.theme.type or "light"
    except AttributeError:
        return "light"


MODE = theme_mode()
T = tokens(MODE)
TEMPLATE = template(MODE)


def show(fig: go.Figure, height: int):
    fig.update_layout(template=TEMPLATE, height=height)
    st.plotly_chart(fig, use_container_width=True, theme=None, config={"displaylogo": False})


def short(sim_id: str) -> str:
    return sim_id[:8]


# --------------------------------------------------------------------------- header

silver, gold, sessions, dq, quarantine = get_lake()
model, model_error = get_model()

st.title("Vehicle Diagnostics")
tracking = AppConfig.MLFLOW_TRACKING_URI
if tracking.startswith("sqlite:"):
    tracking = f"sqlite · {Path(tracking.split(':///', 1)[-1]).name}"  # no local paths on screen
st.caption(
    f"Lake: `{AppConfig.STORAGE_MODE}` · MLflow: `{tracking}`"
    + (f" · model `{AppConfig.MODEL_NAME}` v{model.version.version}" if model else "")
)

if silver.empty:
    st.info(
        "The lake is empty. Generate sessions and run the pipelines first:\n\n"
        "```\npython app/runtimes/generate_sessions.py --sessions 12 --minutes 3\n"
        "python app/runtimes/run_pipelines.py\npython app/runtimes/run_ml_datasets.py\n```"
    )
    st.stop()

if not gold.empty and model is not None:
    gold = gold.assign(p_aggressive=get_predictions(model, gold, model.version.version))

tab_overview, tab_replay, tab_model, tab_quality = st.tabs(["Overview", "Session replay", "Model", "Data quality"])


# --------------------------------------------------------------------------- overview

with tab_overview:
    latest_dq = dq.iloc[-1] if not dq.empty else None
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sessions", f"{len(sessions)}")
    c2.metric("Telemetry ticks (Silver)", f"{len(silver):,}".replace(",", " "))
    if latest_dq is not None:
        invalid = int(latest_dq["invalid_rows"])
        c3.metric(
            "Rows in quarantine (last run)",
            f"{invalid}",
            help="Rows rejected by the Silver null / range checks",
        )
    else:
        c3.metric("Rows in quarantine", "–")
    if model is not None and "roc_auc" in model.metrics:
        c4.metric(
            "Model ROC-AUC",
            f"{model.metrics['roc_auc']:.2f}",
            f"accuracy {model.metrics['accuracy']:.2f} vs {model.metrics['baseline_accuracy']:.2f} baseline",
            delta_color="off",
        )
    else:
        c4.metric("Model ROC-AUC", "–", help=model_error)

    left, right = st.columns([2, 3])

    with left:
        st.subheader("High-wear windows by driver profile")
        st.caption("Share of 10-second windows labelled AGGRESSIVE (top 25 % engine wear rate).")
        if not gold.empty:
            by_profile = (
                gold.merge(sessions[["simulation_id", "driver_profile"]], on="simulation_id")
                .assign(is_aggr=lambda d: d[TARGET_COLUMN] == POSITIVE_CLASS)
                .groupby("driver_profile")["is_aggr"].mean()
            )
            order = [p for p in PROFILE_ORDER if p in by_profile.index]
            colors = profile_colors(MODE)
            fig = go.Figure(go.Bar(
                x=[by_profile[p] for p in order], y=order, orientation="h",
                marker=dict(color=[colors[p] for p in order], line=dict(color=T["surface"], width=2)),
                text=[f"{by_profile[p]:.0%}" for p in order], textposition="outside",
                textfont=dict(color=T["ink"]), cliponaxis=False,
                hovertemplate="%{y}: %{x:.1%} of windows<extra></extra>",
            ))
            fig.update_xaxes(tickformat=".0%", range=[0, max(0.05, by_profile.max() * 1.25)])
            fig.update_yaxes(categoryorder="array", categoryarray=order[::-1], showgrid=False)
            show(fig, 260)

    with right:
        st.subheader("Sessions")
        table = sessions.assign(session=sessions["simulation_id"].map(short)).drop(columns="simulation_id")
        if "aggressive_share" in table:
            table["aggressive_share"] = table["aggressive_share"] * 100
        st.dataframe(
            table[["session", "driver_profile", "split", "duration_s", "max_speed_kmh", "avg_rpm",
                   "max_oil_temp_c", "wear_gained", "aggressive_share"]],
            hide_index=True,
            use_container_width=True,
            height=300,
            column_config={
                "session": "Session",
                "driver_profile": "Driver",
                "split": "Split",
                "duration_s": st.column_config.NumberColumn("Duration (s)", format="%d"),
                "max_speed_kmh": st.column_config.NumberColumn("Max speed (km/h)", format="%d"),
                "avg_rpm": st.column_config.NumberColumn("Avg RPM", format="%d"),
                "max_oil_temp_c": st.column_config.NumberColumn("Max oil (°C)", format="%d"),
                "wear_gained": st.column_config.NumberColumn("Wear gained", format="%.3f"),
                "aggressive_share": st.column_config.ProgressColumn(
                    "High-wear windows", format="%.0f%%", min_value=0, max_value=100),
            },
        )


# --------------------------------------------------------------------------- session replay

def contiguous_runs(steps: pd.Series, flags: pd.Series) -> list[tuple[float, float]]:
    """(start, end) of each run of consecutive True flags."""
    runs, start, prev = [], None, None
    for step, flag in zip(steps, flags):
        if flag and start is None:
            start = step
        if not flag and start is not None:
            runs.append((start, prev))
            start = None
        prev = step
    if start is not None:
        runs.append((start, prev))
    return runs


with tab_replay:
    labels = {
        row.simulation_id: f"{short(row.simulation_id)} · {row.driver_profile} · {row.split} · {int(row.duration_s)} s"
        for row in sessions.itertuples()
    }
    test_first = sorted(labels, key=lambda s: (sessions.set_index("simulation_id").loc[s, "split"] != "test", s))
    sim_id = st.selectbox("Session", test_first, format_func=labels.get,
                          help="Test sessions first: the model never saw them during training.")

    s = silver[silver["simulation_id"] == sim_id]
    g = gold[gold["simulation_id"] == sim_id] if not gold.empty else gold
    t_by_step = dict(zip(s["step"], s["simulation_time"]))

    panels = [
        ("speed_kmh", "Speed (km/h)", s),
        ("engine_rpm", "Engine RPM", s),
        ("oil_temp_c", "Oil temperature (°C)", s),
        ("engine_wear", "Engine wear (cumulative)", s),
    ]
    has_model = "p_aggressive" in g.columns and not g.empty
    rows = len(panels) + (1 if has_model else 0)
    titles = [p[1] for p in panels] + (["Model: P(high wear) vs ground truth"] if has_model else [])
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=titles)

    for i, (col, title, frame) in enumerate(panels, start=1):
        fig.add_trace(go.Scatter(
            x=frame["simulation_time"], y=frame[col], mode="lines", name=title, showlegend=False,
            line=dict(color=T["series"][0], width=2),
            hovertemplate=f"{title}: %{{y:,.1f}}<extra></extra>" if col != "engine_wear"
            else f"{title}: %{{y:.4f}}<extra></extra>",
        ), row=i, col=1)

    if not g.empty:
        # Ground-truth high-wear windows shaded across every panel
        for start, end in contiguous_runs(g["step"], g[TARGET_COLUMN] == POSITIVE_CLASS):
            fig.add_vrect(x0=t_by_step.get(start, start / 10), x1=t_by_step.get(end, end / 10),
                          fillcolor=T["highlight"], line_width=0, layer="below")
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers", name="High-wear window (ground truth)",
            marker=dict(symbol="square", size=12, color=T["highlight_legend"]),
        ))

    if has_model:
        times = g["step"].map(t_by_step)
        fig.add_trace(go.Scatter(
            x=times, y=g["p_aggressive"], mode="lines", name="Model P(high wear)",
            line=dict(color=T["series"][0], width=2),
            hovertemplate="P(high wear): %{y:.0%}<extra></extra>",
        ), row=rows, col=1)
        fig.add_hline(y=0.5, line=dict(color=T["muted"], width=1, dash="dot"), row=rows, col=1)
        fig.update_yaxes(range=[0, 1], tickformat=".0%", row=rows, col=1)

    fig.update_xaxes(title_text="Simulated time (s)", row=rows, col=1)
    fig.update_layout(hovermode="x unified")
    fig.update_annotations(font=dict(size=13, color=T["ink_secondary"]), x=0, xanchor="left")
    show(fig, 170 * rows + 60)

    if has_model:
        hits = ((g["p_aggressive"] > 0.5) == (g[TARGET_COLUMN] == POSITIVE_CLASS)).mean()
        st.caption(f"In this session the model agrees with the ground truth on {hits:.0%} of windows "
                   f"(threshold 50 %). The model only sees RPM, load, throttle, speed, gear and oil "
                   f"temperature; wear itself is never an input.")


# --------------------------------------------------------------------------- model

with tab_model:
    if model is None:
        st.warning(f"No trained model available. Run `python app/runtimes/run_ml_datasets.py`.\n\n{model_error}")
    else:
        m = model.metrics
        st.caption(f"Run `{model.run.info.run_id[:8]}` · {int(m.get('train_rows', 0)):,} training rows · "
                   f"{int(m.get('test_rows', 0)):,} test rows from sessions the model never saw".replace(",", " "))

        left, right = st.columns(2)
        with left:
            st.subheader("Model vs always-NORMAL baseline")
            names = ["Accuracy", "F1 (high wear)", "ROC-AUC"]
            model_vals = [m.get("accuracy"), m.get("f1_aggressive"), m.get("roc_auc")]
            base_vals = [m.get("baseline_accuracy"), 0.0, 0.5]
            fig = go.Figure([
                go.Bar(x=names, y=model_vals, name="Model", marker=dict(color=T["series"][0]),
                       text=[f"{v:.2f}" for v in model_vals], textposition="outside", cliponaxis=False,
                       textfont=dict(color=T["ink"]), hovertemplate="Model %{x}: %{y:.3f}<extra></extra>"),
                go.Bar(x=names, y=base_vals, name="Baseline", marker=dict(color=T["baseline"]),
                       text=[f"{v:.2f}" for v in base_vals], textposition="outside", cliponaxis=False,
                       textfont=dict(color=T["ink_secondary"]), hovertemplate="Baseline %{x}: %{y:.3f}<extra></extra>"),
            ])
            fig.update_layout(barmode="group", bargroupgap=0.08)
            fig.update_yaxes(range=[0, 1.12], dtick=0.25)
            fig.update_xaxes(showgrid=False)
            show(fig, 320)

        with right:
            st.subheader("Confusion matrix on test sessions")
            if not gold.empty:
                _, test_ids = split_simulation_ids(gold["simulation_id"].unique())
                test = gold[gold["simulation_id"].isin(test_ids)]
                actual = np.where(test[TARGET_COLUMN] == POSITIVE_CLASS, "High wear", "Normal")
                predicted = np.where(test["p_aggressive"] > 0.5, "High wear", "Normal")
                order = ["Normal", "High wear"]
                cm = pd.crosstab(pd.Categorical(actual, order), pd.Categorical(predicted, order), dropna=False)
                share = cm.div(cm.sum(axis=1), axis=0)
                xs, ys = [f"Predicted {o.lower()}" for o in order], [f"Actual {o.lower()}" for o in order]
                text = [[f"{cm.iat[i, j]:,}<br>{share.iat[i, j]:.0%}".replace(",", " ") for j in range(2)] for i in range(2)]
                ramp = T["sequential"]
                fig = go.Figure(go.Heatmap(
                    z=share.values, x=xs, y=ys, text=text,
                    colorscale=[[k / (len(ramp) - 1), c] for k, c in enumerate(ramp)],
                    zmin=0, zmax=1, showscale=False, xgap=2, ygap=2,
                    hovertemplate="%{y}, %{x}: %{text}<extra></extra>",
                ))
                # Label ink follows the cell's lightness so every number stays readable
                light_cells = (lambda v: v < 0.5) if MODE == "light" else (lambda v: v >= 0.5)
                for i in range(2):
                    for j in range(2):
                        fig.add_annotation(x=xs[j], y=ys[i], text=text[i][j], showarrow=False,
                                           font=dict(size=15, color="#ffffff" if not light_cells(share.iat[i, j]) else "#0b0b0b"))
                fig.update_yaxes(autorange="reversed", showgrid=False)
                fig.update_xaxes(showgrid=False, side="top")
                show(fig, 320)
                st.caption("Percentages are per actual class (recall).")

        left, right = st.columns(2)
        with left:
            st.subheader("Feature importance")
            imp = model.feature_importance()
            fig = go.Figure(go.Bar(
                x=imp.values, y=[FEATURE_LABELS.get(f, f) for f in imp.index], orientation="h",
                marker=dict(color=T["series"][0]),
                hovertemplate="%{y}: %{x:.3f}<extra></extra>",
            ))
            fig.update_yaxes(showgrid=False)
            fig.update_xaxes(title_text="Mean decrease in impurity")
            show(fig, 360)

        with right:
            st.subheader("Training runs")
            history = model.run_history()
            if len(history) > 1:
                fig = go.Figure()
                for i, (col, name) in enumerate([("roc_auc", "ROC-AUC"), ("accuracy", "Accuracy")]):
                    if col in history:
                        fig.add_trace(go.Scatter(x=history.index + 1, y=history[col], name=name, mode="lines+markers",
                                                 line=dict(color=T["series"][i], width=2), marker=dict(size=8)))
                if "baseline_accuracy" in history:
                    fig.add_trace(go.Scatter(x=history.index + 1, y=history["baseline_accuracy"], name="Baseline accuracy",
                                             mode="lines", line=dict(color=T["muted"], width=2, dash="dot")))
                fig.update_xaxes(title_text="Run", dtick=1)
                fig.update_yaxes(range=[0, 1])
                fig.update_layout(hovermode="x unified")
                show(fig, 360)
            else:
                st.caption("Only one training run so far; retrain to see the trend.")
            st.dataframe(history.round(3), hide_index=True, use_container_width=True)


# --------------------------------------------------------------------------- data quality

with tab_quality:
    st.caption("Every Silver run checks nulls and physical ranges (RPM 0–10 000, speed 0–500 km/h, "
               "throttle 0–1.1, coolant −50–250 °C). Failing rows go to quarantine instead of being dropped.")
    if dq.empty:
        st.info("No data quality metrics yet: run `python app/runtimes/run_pipelines.py`.")
    else:
        last = dq.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows checked (last run)", f"{int(last['total_rows']):,}".replace(",", " "))
        c2.metric("Null violations", int(last["null_violations"]))
        c3.metric("Range violations", int(last["range_violations"]))
        ok = int(last["invalid_rows"]) == 0
        c4.metric("Quarantined rows", "✓ 0" if ok else f"⚠ {int(last['invalid_rows'])}",
                  help="Rows that failed a check in the last Silver run; listed below with the reason")

        st.subheader("Quarantined rows per Silver run")
        hist = dq.copy()
        hist["run"] = pd.to_datetime(hist["check_time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        fig = go.Figure(go.Bar(
            x=hist["run"], y=hist["invalid_rows"], marker=dict(color=T["series"][1]),
            text=[f"{int(v)} of {int(t):,}".replace(",", " ") for v, t in zip(hist["invalid_rows"], hist["total_rows"])],
            textposition="outside", cliponaxis=False, textfont=dict(color=T["ink"]),
            hovertemplate="%{x}: %{y} quarantined<extra></extra>",
        ))
        fig.update_layout(bargap=0.6 if len(hist) < 4 else 0.25)
        fig.update_xaxes(showgrid=False, type="category", title_text="Silver run")
        fig.update_yaxes(title_text="Rows", rangemode="tozero", range=[0, max(1, hist["invalid_rows"].max()) * 1.3])
        show(fig, 280)

    st.subheader("Quarantine")
    if quarantine.empty:
        st.caption("No rows in quarantine.")
    else:
        q = quarantine.copy()
        q["reason"] = np.select(
            [q["is_null_violation"].fillna(False).astype(bool), q["is_range_violation"].fillna(False).astype(bool)],
            ["missing value", "out of range"], "other")
        st.dataframe(q[["simulation_id", "step", "reason", "engine_rpm", "speed_kmh", "throttle", "coolant_temp_c"]],
                     hide_index=True, use_container_width=True)
