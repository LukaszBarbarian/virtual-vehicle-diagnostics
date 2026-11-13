"""
Chart colours and the Plotly template, for light and dark mode.
Categorical slots follow a fixed, colour-blind-validated order and are never cycled.
"""
import plotly.graph_objects as go

TOKENS = {
    "light": {
        "surface": "#fcfcfb",
        "ink": "#0b0b0b",
        "ink_secondary": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "axis": "#c3c2b7",
        "series": ["#2a78d6", "#eb6834", "#1baf7a"],
        "sequential": ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
        "baseline": "#c3c2b7",
        "highlight": "rgba(235, 104, 52, 0.16)",
        "highlight_legend": "rgba(235, 104, 52, 0.55)",
    },
    "dark": {
        "surface": "#1a1a19",
        "ink": "#f0efec",
        "ink_secondary": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
        "series": ["#3987e5", "#d95926", "#199e70"],
        "sequential": ["#0d366b", "#104281", "#184f95", "#1c5cab", "#256abf", "#3987e5", "#86b6ef"],
        "baseline": "#5c5b57",
        "highlight": "rgba(217, 89, 38, 0.22)",
        "highlight_legend": "rgba(217, 89, 38, 0.65)",
    },
}

STATUS = {"good": "#0ca30c", "critical": "#d03b3b"}

# Driver profiles keep the same colour everywhere, whatever is filtered
PROFILE_ORDER = ["eco", "normal", "sport", "unknown"]


def tokens(mode: str) -> dict:
    return TOKENS["dark" if mode == "dark" else "light"]


def profile_colors(mode: str) -> dict:
    t = tokens(mode)
    return {"eco": t["series"][0], "normal": t["series"][1], "sport": t["series"][2], "unknown": t["muted"]}


def template(mode: str) -> go.layout.Template:
    t = tokens(mode)
    axis = dict(
        gridcolor=t["grid"], gridwidth=1, linecolor=t["axis"], zeroline=False, automargin=True,
        tickfont=dict(color=t["muted"], size=11), title=dict(font=dict(color=t["ink_secondary"], size=12)),
    )
    return go.layout.Template(layout=dict(
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=t["ink"], size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=t["series"],
        xaxis=axis,
        yaxis=axis,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=t["ink_secondary"], size=12)),
        hoverlabel=dict(bgcolor=t["surface"], bordercolor=t["axis"], font=dict(color=t["ink"])),
        margin=dict(l=8, r=8, t=36, b=8),
        bargap=0.25,
        barcornerradius=4,
    ))
