from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QRectF

class ControlBar(QWidget):
    def __init__(self, horizontal=False, color="#2ecc71"):
        super().__init__()
        self.horizontal = horizontal
        self.bar_color = color
        self.value = 0.0

    def set_value(self, v: float):
        self.value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#1a1a1a"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 5, 5)

        margin = 3
        if self.horizontal:
            w = (self.width() - (margin * 2)) * self.value
            rect = QRectF(margin, margin, w, self.height() - (margin * 2))
        else:
            h = (self.height() - (margin * 2)) * self.value
            rect = QRectF(margin, self.height() - h - margin, self.width() - (margin * 2), h)
        
        painter.setBrush(QColor(self.bar_color))
        painter.drawRoundedRect(rect, 3, 3)