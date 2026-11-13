from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget

from ui2.theme import font, qcolor


class ControlBar(QWidget):
    """
    Slim pedal bar with a gradient fill, its value in percent and a caption (e.g. THROTTLE).
    """

    def __init__(self, horizontal=False, color="#22d3ee", caption: str = ""):
        super().__init__()
        self.horizontal = horizontal
        self.bar_color = QColor(color)
        self.caption = caption
        self.value = 0.0
        if not horizontal:
            self.setMinimumWidth(44)

    def set_value(self, v: float):
        self.value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _):
        with QPainter(self) as p:
            p.setRenderHint(QPainter.Antialiasing)
            r = QRectF(self.rect())
            caption_h = 34 if self.caption and not self.horizontal else 0
            track = r.adjusted(8, 22, -8, -caption_h) if not self.horizontal else r.adjusted(0, 0, 0, 0)

            p.setPen(Qt.NoPen)
            p.setBrush(qcolor("track"))
            radius = min(track.width(), track.height()) / 2
            p.drawRoundedRect(track, radius, radius)

            if self.value > 0:
                if self.horizontal:
                    fill = QRectF(track.left(), track.top(), track.width() * self.value, track.height())
                    grad = QLinearGradient(fill.topLeft(), fill.topRight())
                else:
                    h = track.height() * self.value
                    fill = QRectF(track.left(), track.bottom() - h, track.width(), h)
                    grad = QLinearGradient(fill.bottomLeft(), fill.topLeft())
                dim = QColor(self.bar_color)
                dim.setAlpha(110)
                grad.setColorAt(0, dim)
                grad.setColorAt(1, self.bar_color)
                p.setBrush(grad)
                p.drawRoundedRect(fill, radius, radius)

            if not self.horizontal:
                p.setPen(qcolor("text"))
                p.setFont(font(9, QFont.DemiBold))
                p.drawText(QRectF(r.left(), r.top(), r.width(), 20), Qt.AlignCenter, f"{self.value * 100:.0f}%")
                if self.caption:
                    p.setPen(qcolor("muted"))
                    p.setFont(font(7, QFont.DemiBold))
                    p.drawText(QRectF(r.left() - 10, r.bottom() - caption_h + 6, r.width() + 20, 24),
                               Qt.AlignHCenter | Qt.AlignTop, self.caption)
