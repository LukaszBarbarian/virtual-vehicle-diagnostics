import math
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtCore import Qt, QRectF

class CircularGauge(QWidget):
    """
    A custom circular gauge widget for displaying automotive-style metrics like RPM or speed.
    """
    def __init__(
        self,
        label: str,
        min_val: float,
        max_val: float,
        redline: float | None = None,
        major_step: float | None = None,
        label_formatter=None,
        scale_font_size: int = 9,
        arc_width: int = 10
    ):
        """
        Initializes the gauge with range settings, styling properties, and angular constraints.
        """
        super().__init__()

        self.label = label
        self.min = min_val
        self.max = max_val
        self.redline = redline
        self.major_step = major_step or (max_val - min_val) / 6
        self.label_formatter = label_formatter or (lambda v: str(int(v)))
        self.value = min_val
        self.scale_font_size = scale_font_size
        self.arc_width = arc_width

        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.start_angle = 135
        self.span_angle = 270 

    def set_value(self, v: float):
        """
        Updates the current needle position within the defined range and refreshes the display.
        """
        self.value = max(self.min, min(self.max, v))
        self.update()

    def set_range(self, min_val: float, max_val: float):
        """
        Redefines the minimum and maximum scale limits and recalculates step increments.
        """
        self.min = min_val
        self.max = max_val
        self.major_step = (max_val - min_val) / 6
        self.update()

    def set_redline(self, redline: float | None):
        """
        Configures the threshold where the gauge transition to the red warning zone.
        """
        self.redline = redline
        self.update()

    def paintEvent(self, _):
        """
        Coordinates the drawing sequence, including scaling, arcs, ticks, needle, and text.
        """
        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.Antialiasing)

            side = min(self.width(), self.height())
            painter.translate(self.width() / 2, self.height() / 2)
            
            scale = side / 250.0
            painter.scale(scale, scale)

            rect = QRectF(-100, -100, 200, 200)

            self._draw_arcs(painter, rect)
            self._draw_ticks_and_labels(painter)
            self._draw_needle(painter)
            self._draw_central_text(painter)

    def _draw_arcs(self, painter, rect):
        """
        Renders the color-coded background arcs (green, yellow, red) based on the current range.
        """
        start_qt = -self.start_angle * 16

        def span(val_from, val_to):
            if self.max == self.min:
                return 0
            ratio_from = (val_from - self.min) / (self.max - self.min)
            ratio_to = (val_to - self.min) / (self.max - self.min)
            return int(-(self.span_angle * (ratio_to - ratio_from)) * 16)

        yellow_start = self.redline * 0.8 if self.redline else self.max * 0.8
        red_start = self.redline if self.redline else self.max

        pen = QPen(Qt.SolidLine)
        pen.setCapStyle(Qt.FlatCap)
        pen.setWidth(self.arc_width)

        pen.setColor(QColor("#2ecc71"))
        painter.setPen(pen)
        painter.drawArc(rect, start_qt, span(self.min, yellow_start))

        pen.setColor(QColor("#f1c40f"))
        painter.setPen(pen)
        painter.drawArc(rect, start_qt + span(self.min, yellow_start), span(yellow_start, red_start))

        pen.setColor(QColor("#e74c3c"))
        painter.setPen(pen)
        painter.drawArc(rect, start_qt + span(self.min, red_start), span(red_start, self.max))

    def _draw_ticks_and_labels(self, painter):
        """
        Draws the graduation marks and numerical labels around the gauge perimeter.
        """
        painter.save()
        
        if self.major_step <= 0: return
        steps = int((self.max - self.min) / self.major_step)
        angle_per_unit = self.span_angle / (self.max - self.min) if self.max != self.min else 0

        for i in range(steps + 1):
            val = self.min + (i * self.major_step)
            angle = self.start_angle + (val - self.min) * angle_per_unit
            
            painter.save()
            painter.rotate(angle)
            
            painter.setPen(QPen(Qt.white, 2))
            painter.drawLine(85, 0, 95, 0)
            
            painter.translate(70, 0)
            painter.rotate(-angle)
            
            painter.setFont(QFont("Arial", self.scale_font_size, QFont.Bold))
            text = self.label_formatter(val)
            metrics = painter.fontMetrics()
            w = metrics.horizontalAdvance(text)
            h = metrics.height()
            painter.drawText(int(-w/2), int(h/4), text)
            
            painter.restore()
            
        painter.restore()

    def _draw_needle(self, painter):
        """
        Renders the physical needle and central hub based on the current gauge value.
        """
        painter.save()
        angle_per_unit = self.span_angle / (self.max - self.min) if self.max != self.min else 0
        angle = self.start_angle + (self.value - self.min) * angle_per_unit
        
        painter.rotate(angle)
        painter.setPen(QPen(QColor("#ffffff"), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(0, 0, 80, 0)
        
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(-5, -5, 10, 10)
        painter.restore()

    def _draw_central_text(self, painter):
        """
        Displays the digital value readout and the descriptive label in the center of the gauge.
        """
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(QRectF(-50, 35, 100, 30), Qt.AlignCenter, str(int(self.value)))
        
        painter.setFont(QFont("Arial", 8))
        painter.drawText(QRectF(-50, 60, 100, 20), Qt.AlignCenter, self.label)