from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QFont

class GearDisplay(QLabel):
    """
    A specialized label widget for displaying the current vehicle transmission gear.
    """
    def __init__(self):
        """
        Initializes the gear display with default neutral 'N' state and custom styling.
        """
        super().__init__("N")
        self.setFont(QFont("Arial", 32, QFont.Bold))
        self.setStyleSheet("color: orange;")

    def set_gear(self, gear: int):
        """
        Updates the displayed text based on the gear index, using 'N' for neutral/park.
        """
        self.setText("N" if gear <= 0 else f"D{gear}")