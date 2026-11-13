from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui2.theme import COLORS, qcolor

# style key -> (status text, icon, colour token)
STATUS = {
    "calm": ("OPTIMAL", "●", "good"),
    "normal": ("CAUTION", "▲", "warning"),
    "aggressive": ("HIGH WEAR", "■", "critical"),
    "neutral": ("WAITING", "○", "muted"),
}


class Sparkline(QWidget):
    """P(high wear) over the last minute, with the 50 % decision line."""

    def __init__(self, capacity: int = 60):
        super().__init__()
        self.values = deque(maxlen=capacity)
        self.setMinimumHeight(54)

    def add(self, value: float):
        self.values.append(max(0.0, min(100.0, value)))
        self.update()

    def clear(self):
        self.values.clear()
        self.update()

    def paintEvent(self, _):
        with QPainter(self) as p:
            p.setRenderHint(QPainter.Antialiasing)
            r = QRectF(self.rect()).adjusted(2, 4, -2, -4)
            mid = r.top() + r.height() * 0.5
            p.setPen(QPen(qcolor("muted"), 1, Qt.DotLine))
            p.drawLine(QPointF(r.left(), mid), QPointF(r.right(), mid))
            if len(self.values) < 2:
                return
            cap = self.values.maxlen
            step = r.width() / (cap - 1)
            x0 = r.right() - step * (len(self.values) - 1)
            pts = [QPointF(x0 + i * step, r.bottom() - r.height() * v / 100) for i, v in enumerate(self.values)]

            area = QPainterPath(QPointF(pts[0].x(), r.bottom()))
            for pt in pts:
                area.lineTo(pt)
            area.lineTo(QPointF(pts[-1].x(), r.bottom()))
            grad = QLinearGradient(0, r.top(), 0, r.bottom())
            grad.setColorAt(0, qcolor("accent", 90))
            grad.setColorAt(1, qcolor("accent", 0))
            p.setPen(Qt.NoPen)
            p.setBrush(grad)
            p.drawPath(area)

            line = QPainterPath(pts[0])
            for pt in pts[1:]:
                line.lineTo(pt)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(qcolor("accent"), 2))
            p.drawPath(line)


class ProbabilityBar(QWidget):
    """Horizontal 0-100 % bar whose colour follows the coach status."""

    def __init__(self):
        super().__init__()
        self.value = 0.0
        self.color = qcolor("muted")
        self.setFixedHeight(10)

    def set(self, value: float, color_token: str):
        self.value = max(0.0, min(100.0, value))
        self.color = qcolor(color_token)
        self.update()

    def paintEvent(self, _):
        with QPainter(self) as p:
            p.setRenderHint(QPainter.Antialiasing)
            r = QRectF(self.rect())
            p.setPen(Qt.NoPen)
            p.setBrush(qcolor("track"))
            p.drawRoundedRect(r, 5, 5)
            if self.value > 0:
                p.setBrush(self.color)
                p.drawRoundedRect(QRectF(r.left(), r.top(), max(10, r.width() * self.value / 100), r.height()), 5, 5)


class CoachingPanel(QFrame):
    """
    AI coach card: status with icon, probability of high engine wear, the wear actually measured
    over the last 10 seconds and a one-minute trend.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("card")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("AI ENGINE COACH")
        title.setObjectName("sectionLabel")
        header.addWidget(title)
        header.addStretch()
        self.status_label = QLabel()
        self.status_label.setObjectName("status")
        header.addWidget(self.status_label)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(4)
        self.score_label = QLabel("–")
        self.score_label.setObjectName("bigNumber")
        left.addWidget(self.score_label)
        caption = QLabel("chance of high engine wear")
        caption.setObjectName("statLabel")
        left.addWidget(caption)
        left.addSpacing(6)
        self.score_bar = ProbabilityBar()
        left.addWidget(self.score_bar)
        left.addSpacing(8)
        self.advice_label = QLabel("Start the engine to begin analysis")
        self.advice_label.setObjectName("statLabel")
        self.advice_label.setWordWrap(True)
        left.addWidget(self.advice_label)
        left.addStretch()
        body.addLayout(left, 2)

        right = QVBoxLayout()
        right.setSpacing(2)
        trend = QLabel("LAST 60 S")
        trend.setObjectName("sectionLabel")
        right.addWidget(trend)
        self.sparkline = Sparkline()
        right.addWidget(self.sparkline, 1)
        body.addLayout(right, 3)

        root.addLayout(body, 1)
        self._set_status("neutral")

    def _set_status(self, style_key: str):
        text, icon, token = STATUS.get(style_key, STATUS["neutral"])
        self.status_label.setText(f"{icon}  {text}")
        self.status_label.setStyleSheet(f"color: {COLORS[token]};")
        return token

    def update_coaching(self, score: float, style_key: str, status_text: str):
        """
        score: smoothed P(high wear) in percent; style_key: calm / normal / aggressive / neutral;
        status_text: secondary line (wear measured, warm-up progress or a message).
        """
        token = self._set_status(style_key)
        if style_key == "neutral":
            self.score_label.setText("–")
            self.score_bar.set(0, "muted")
        else:
            self.score_label.setText(f"{score:.0f}%")
            self.score_bar.set(score, token)
            self.sparkline.add(score)
        self.advice_label.setText(status_text)

    def reset(self):
        self.sparkline.clear()
        self.update_coaching(0.0, "neutral", "Start the engine to begin analysis")
