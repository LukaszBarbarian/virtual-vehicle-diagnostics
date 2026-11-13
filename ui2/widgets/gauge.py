from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QConicalGradient, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ui2.theme import font, qcolor


class CircularGauge(QWidget):
    """
    Modern arc gauge: a thin track, a gradient progress arc, a marked redline zone and a large
    digital readout in the centre. The arc turns red once the value enters the redline zone.
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
        arc_width: int = 10,
        unit: str = "",
        value_formatter=None,
        color_for_value=None,
    ):
        super().__init__()
        self.label = label
        self.unit = unit
        self.min = min_val
        self.max = max_val
        self.redline = redline
        self.major_step = major_step or (max_val - min_val) / 6
        self.label_formatter = label_formatter or (lambda v: str(int(v)))
        self.value_formatter = value_formatter or (lambda v: f"{v:.0f}")
        self.color_for_value = color_for_value
        self.value = min_val
        self.scale_font_size = scale_font_size
        self.arc_width = arc_width

        self.start_angle = 225  # degrees, Qt convention (counter-clockwise from 3 o'clock)
        self.span_angle = 270

        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # ------------------------------------------------------------------ API

    def set_value(self, v: float):
        self.value = max(self.min, min(self.max, v))
        self.update()

    def set_range(self, min_val: float, max_val: float):
        self.min, self.max = min_val, max_val
        self.major_step = (max_val - min_val) / 6
        self.update()

    def set_redline(self, redline: float | None):
        self.redline = redline
        self.update()

    # ------------------------------------------------------------------ painting

    def _ratio(self, v: float) -> float:
        return 0.0 if self.max == self.min else (v - self.min) / (self.max - self.min)

    def _angle(self, v: float) -> float:
        return self.start_angle - self.span_angle * self._ratio(v)

    def paintEvent(self, _):
        with QPainter(self) as p:
            p.setRenderHint(QPainter.Antialiasing)
            side = min(self.width(), self.height())
            p.translate(self.width() / 2, self.height() / 2 + side * 0.04)
            p.scale(side / 250.0, side / 250.0)

            rect = QRectF(-100, -100, 200, 200)
            in_redline = self.redline is not None and self.value >= self.redline

            # Track
            pen = QPen(qcolor("track"), self.arc_width, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(rect, int(self.start_angle * 16), int(-self.span_angle * 16))

            # Redline zone, drawn just outside the track
            if self.redline is not None and self.redline < self.max:
                outer = QRectF(-110, -110, 220, 220)
                p.setPen(QPen(qcolor("critical", 200), 3, Qt.SolidLine, Qt.FlatCap))
                a0 = self._angle(self.redline)
                p.drawArc(outer, int(a0 * 16), int(-(a0 - self._angle(self.max)) * 16))

            # Progress arc
            ratio = self._ratio(self.value)
            if ratio > 0.002:
                if self.color_for_value:
                    brush = qcolor(self.color_for_value(self.value))
                elif in_redline:
                    brush = qcolor("critical")
                else:
                    grad = QConicalGradient(QPointF(0, 0), self.start_angle)
                    grad.setColorAt(0.0, qcolor("accent_2"))
                    grad.setColorAt(self.span_angle / 360.0, qcolor("accent"))
                    brush = grad
                pen = QPen(brush, self.arc_width, Qt.SolidLine, Qt.RoundCap)
                p.setPen(pen)
                p.drawArc(rect, int(self.start_angle * 16), int(-self.span_angle * ratio * 16))

                # Glowing tip
                tip_angle = self._angle(self.value)
                p.save()
                p.rotate(-tip_angle)
                p.setPen(Qt.NoPen)
                tip = qcolor(self.color_for_value(self.value)) if self.color_for_value else (
                    qcolor("critical") if in_redline else qcolor("accent"))
                tip.setAlpha(70)
                p.setBrush(tip)
                p.drawEllipse(QPointF(100, 0), self.arc_width * 0.9, self.arc_width * 0.9)
                p.restore()

            self._draw_scale(p)
            self._draw_readout(p, in_redline)

    def _draw_scale(self, p: QPainter):
        if self.major_step <= 0 or self.max == self.min:
            return
        if self.scale_font_size < 8:
            return  # small gauges show only the arc and the readout
        p.setFont(font(self.scale_font_size * 0.8))
        steps = int(round((self.max - self.min) / self.major_step))
        for i in range(steps + 1):
            val = self.min + i * self.major_step
            angle = self._angle(val)
            p.save()
            p.rotate(-angle)
            p.translate(78, 0)
            p.rotate(angle)
            color = "critical" if self.redline is not None and val >= self.redline else "muted"
            p.setPen(qcolor(color))
            p.drawText(QRectF(-16, -8, 32, 16), Qt.AlignCenter, self.label_formatter(val))
            p.restore()

    def _draw_readout(self, p: QPainter, in_redline: bool):
        p.setPen(qcolor("critical") if in_redline else qcolor("text"))
        small = self.scale_font_size < 8
        p.setFont(font(40 if small else 30, QFont.DemiBold))
        p.drawText(QRectF(-90, -40 if small else -30, 180, 60 if small else 50), Qt.AlignCenter,
                   self.value_formatter(self.value))
        p.setPen(qcolor("text_secondary"))
        p.setFont(font(14 if small else 8.5, QFont.Medium))
        p.drawText(QRectF(-90, 24 if small else 18, 180, 30 if small else 20), Qt.AlignCenter,
                   self.unit or self.label)
        if self.unit:
            p.setPen(qcolor("muted"))
            p.setFont(font(12 if small else 7.5, QFont.DemiBold))
            p.drawText(QRectF(-90, 62, 180, 26 if small else 18), Qt.AlignCenter, self.label.upper())
