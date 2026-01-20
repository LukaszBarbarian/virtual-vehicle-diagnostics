from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QFont

class GearDisplay(QLabel):
    def __init__(self):
        super().__init__("N")
        self.setFont(QFont("Arial", 32, QFont.Bold))
        self.setStyleSheet("color: orange;")

    def set_gear(self, gear: int):
        self.setText("N" if gear <= 0 else f"D{gear}")
