from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QPlainTextEdit, QProgressBar
)


from PySide6.QtWidgets import QProgressBar, QFrame

class CoachingPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(200) 
        self.setStyleSheet("background-color: #1a1a1a; border-radius: 5px; border: 1px solid #333;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Tytuł
        title = QLabel("LIVE COACHING")
        title.setStyleSheet("color: #f1c40f; font-weight: bold; border: none; font-size: 10px;")
        layout.addWidget(title)

        # Pasek zdrowia silnika (Engine Health)
        self.health_bar = QProgressBar()
        self.health_bar.setFixedHeight(15)
        self.health_bar.setRange(0, 100)
        self.health_bar.setValue(100)
        self.health_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #444; border-radius: 2px; text-align: center; color: white; font-size: 9px; }
            QProgressBar::chunk { background-color: #2ecc71; }
        """)
        layout.addWidget(self.health_bar)

        # Alerty i status
        self.alerts = QLabel("Status: OK")
        self.alerts.setWordWrap(True)
        self.alerts.setStyleSheet("color: #95a5a6; font-size: 10px; border: none;")
        layout.addWidget(self.alerts)

    def update_coaching(self, health_score, warnings):
        """
        Updates the panel with new prediction and safety warnings.
        health_score: float (0.0 - 100.0)
        warnings: list of strings
        """
        # 1. Aktualizacja paska (kolor zmienia się od zielonego do czerwonego)
        val = int(health_score)
        self.health_bar.setValue(val)
        
        if val > 80:
            color = "#2ecc71" # Zielony
        elif val > 50:
            color = "#f1c40f" # Żółty
        else:
            color = "#e74c3c" # Czerwony
            
        self.health_bar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid #444; border-radius: 2px; text-align: center; color: white; font-size: 9px; }}
            QProgressBar::chunk {{ background-color: {color}; }}
        """)

        # 2. Aktualizacja tekstu alertów
        if warnings:
            # Łączymy ostrzeżenia w listę punktową
            text = "\n".join([f"• {w}" for w in warnings])
            self.alerts.setText(text)
            self.alerts.setStyleSheet("color: #e74c3c; font-size: 10px; border: none; font-weight: bold;")
        else:
            self.alerts.setText("Status: Safe Driving")
            self.alerts.setStyleSheet("color: #2ecc71; font-size: 10px; border: none;")