"""
Cockpit design tokens and the application stylesheet (dark, card-based).
"""
from PySide6.QtGui import QColor, QFont

FONT_FAMILY = "Segoe UI"

COLORS = {
    "bg": "#0b0e13",
    "card": "#141922",
    "card_border": "#1f2632",
    "track": "#232b38",
    "text": "#e8edf4",
    "text_secondary": "#9aa6b8",
    "muted": "#5f6b7d",
    "accent": "#38bdf8",
    "accent_2": "#6366f1",
    "good": "#22c55e",
    "warning": "#f59e0b",
    "critical": "#ef4444",
    "cold": "#60a5fa",
    "throttle": "#22d3ee",
    "brake": "#f43f5e",
}


def qcolor(name: str, alpha: int | None = None) -> QColor:
    color = QColor(COLORS.get(name, name))
    if alpha is not None:
        color.setAlpha(alpha)
    return color


def font(size: float, weight: QFont.Weight = QFont.Normal) -> QFont:
    f = QFont(FONT_FAMILY)
    f.setPointSizeF(size)
    f.setWeight(weight)
    return f


STYLESHEET = f"""
QWidget {{
    background: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: "{FONT_FAMILY}";
    font-size: 10pt;
}}
QFrame#card {{
    background: {COLORS['card']};
    border: 1px solid {COLORS['card_border']};
    border-radius: 16px;
}}
QFrame#card QWidget {{ background: transparent; }}
QLabel#appTitle {{ font-size: 15pt; font-weight: 700; }}
QLabel#appSubtitle {{ color: {COLORS['muted']}; font-size: 9pt; }}
QLabel#sectionLabel {{
    color: {COLORS['muted']}; font-size: 8pt; font-weight: 600; letter-spacing: 1px;
}}
QLabel#statValue {{ font-size: 13pt; font-weight: 600; }}
QLabel#bigNumber {{ font-size: 26pt; font-weight: 600; }}
QLabel#status {{ font-size: 10pt; font-weight: 700; }}
QLabel#carName {{ color: {COLORS['text_secondary']}; font-size: 9pt; }}
QLabel#statLabel {{ color: {COLORS['text_secondary']}; font-size: 9pt; }}
QFrame#card QLabel#chip {{
    background: {COLORS['track']}; color: {COLORS['text_secondary']};
    border-radius: 9px; padding: 3px 9px; font-size: 8.5pt;
}}
QComboBox {{
    background: {COLORS['track']}; border: 1px solid {COLORS['card_border']};
    border-radius: 10px; padding: 7px 12px; font-size: 10pt;
}}
QComboBox:hover {{ border-color: {COLORS['accent']}; }}
QComboBox:disabled {{ color: {COLORS['muted']}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {COLORS['card']}; border: 1px solid {COLORS['card_border']};
    selection-background-color: {COLORS['track']}; padding: 4px; outline: none;
}}
QPushButton#startButton {{
    border: none; border-radius: 14px; padding: 14px; font-size: 12pt; font-weight: 700;
    letter-spacing: 1px;
}}
QPlainTextEdit#log {{
    background: transparent; border: none; color: {COLORS['text_secondary']};
    font-family: "Cascadia Mono", "Consolas", monospace; font-size: 8.5pt;
}}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {COLORS['track']}; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QToolTip {{ background: {COLORS['card']}; color: {COLORS['text']}; border: 1px solid {COLORS['card_border']}; }}
"""

START_STYLE = f"QPushButton#startButton {{ background: {COLORS['good']}; color: #04130a; }}" \
              f"QPushButton#startButton:hover {{ background: #4ade80; }}"
STOP_STYLE = f"QPushButton#startButton {{ background: {COLORS['critical']}; color: white; }}" \
             f"QPushButton#startButton:hover {{ background: #f87171; }}"
