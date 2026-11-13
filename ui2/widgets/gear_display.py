from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ui2.theme import font, qcolor


class GearDisplay(QWidget):
    """
    Large gear indicator in a rounded tile: N when idle, the gear number while driving.
    """

    def __init__(self):
        super().__init__()
        self.gear = 0
        self.setFixedSize(96, 104)

    def set_gear(self, gear: int):
        self.gear = gear
        self.update()

    def paintEvent(self, _):
        with QPainter(self) as p:
            p.setRenderHint(QPainter.Antialiasing)
            r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
            p.setPen(QPen(qcolor("card_border"), 1))
            p.setBrush(qcolor("track", 120))
            p.drawRoundedRect(r, 18, 18)

            p.setPen(qcolor("muted"))
            p.setFont(font(7.5, QFont.DemiBold))
            p.drawText(r.adjusted(0, 10, 0, 0), Qt.AlignHCenter | Qt.AlignTop, "GEAR")

            driving = self.gear > 0
            p.setPen(qcolor("accent") if driving else qcolor("text_secondary"))
            p.setFont(font(34, QFont.Bold))
            p.drawText(r.adjusted(0, 14, 0, 0), Qt.AlignCenter, str(self.gear) if driving else "N")
