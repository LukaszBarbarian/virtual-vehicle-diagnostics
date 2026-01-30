from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QRectF

class ControlBar(QWidget):
    """
    A custom widget that renders a vertical or horizontal progress bar using QPainter.
    """
    def __init__(self, horizontal=False, color="#2ecc71"):
        """
        Initializes the control bar orientation, primary color, and default value.
        """
        super().__init__()
        self.horizontal = horizontal
        self.bar_color = color
        self.value = 0.0

    def set_value(self, v: float):
        """
        Sets the bar level (0.0 to 1.0) and triggers a repaint of the widget.
        """
        self.value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _):
        """
        Handles the custom drawing logic for the background and the dynamic value indicator.
        """
        with QPainter(self) as painter:
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