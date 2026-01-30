from PySide6.QtWidgets import QProgressBar, QFrame, QVBoxLayout, QLabel

class CoachingPanel(QFrame):
    """
    UI panel that displays real-time AI driving coaching feedback and progress bars.
    """
    def __init__(self):
        """
        Initializes the panel layout, visual styles, and default state of the widgets.
        """
        super().__init__()
        self.setFixedWidth(210)
        self.setStyleSheet(
            "background-color: #121212; border: 1px solid #333; border-radius: 4px;"
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        self.label_main = QLabel("AI DRIVING COACH")
        self.label_main.setStyleSheet(
            "color: #f1c40f; font-weight: bold; font-size: 11px;"
        )
        layout.addWidget(self.label_main)

        self.score_bar = QProgressBar()
        self.score_bar.setFixedHeight(18)
        self.score_bar.setRange(0, 100)
        self.score_bar.setTextVisible(False)
        layout.addWidget(self.score_bar)

        self.advice_label = QLabel("Analyzing driving style...")
        self.advice_label.setWordWrap(True)
        self.advice_label.setStyleSheet(
            "color: #ecf0f1; font-size: 10px;"
        )
        layout.addWidget(self.advice_label)

        self._styles = {
            "neutral": """
                QProgressBar { border: 1px solid #444; background: #1e1e1e; }
                QProgressBar::chunk { background-color: #555555; }
            """,
            "calm": """
                QProgressBar { border: 1px solid #444; background: #1e1e1e; }
                QProgressBar::chunk { background-color: #2ecc71; }
            """,
            "normal": """
                QProgressBar { border: 1px solid #444; background: #1e1e1e; }
                QProgressBar::chunk { background-color: #f1c40f; }
            """,
            "aggressive": """
                QProgressBar { border: 1px solid #444; background: #1e1e1e; }
                QProgressBar::chunk { background-color: #e74c3c; }
            """
        }

        self._current_style = None
        self._last_text = None

        self._apply_style("neutral")
        self.score_bar.setValue(0)

    def update_coaching(self, score: float, style_key: str, status_text: str):
        """
        Updates the UI components with the provided driving score, visual style, and advice text.
        """
        self.score_bar.setValue(int(score))
        self._apply_style(style_key)
        self.advice_label.setText(status_text)

    def _apply_style(self, style_name: str):
        """
        Applies a specific stylesheet to the progress bar based on the driving style key.
        """
        if style_name != self._current_style:
            self.score_bar.setStyleSheet(self._styles[style_name])
            self._current_style = style_name

    def _set_text(self, text: str):
        """
        Updates the advice label text only if the new content differs from the previous one.
        """
        if text != self._last_text:
            self.advice_label.setText(text)
            self._last_text = text