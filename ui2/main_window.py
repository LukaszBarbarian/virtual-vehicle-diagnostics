import math
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QPlainTextEdit
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot

from app.runtime import ApplicationRuntime
from ui2.profile_loader import load_car_profile
from ui2.widgets.control_bar import ControlBar
from ui2.widgets.gauge import CircularGauge
from ui2.widgets.gear_display import GearDisplay

class MainWindow(QWidget):
    # Sygnał do bezpiecznego przesyłania logów z wątku symulacji do wątku UI
    log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vehicle Simulator Pro")
        self.setFixedSize(1150, 800)

        self.engine_running = False
        self.car_profile = None
        
        # Statystyki sesji
        self.session_ticks = 0
        self.sum_speed = 0.0
        self.sum_fuel = 0.0
        self.sum_wear = 0.0
        self.throttle_val = 0.0
        self.brake_val = 0.0
        
        # Infrastruktura
        self.app_runtime = ApplicationRuntime("localhost:9092")
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._tick)
        self.log_signal.connect(self.log)
        
        self._build_ui()
        self._load_profiles()
        self._apply_off_state()
        self._apply_start_style()

    def _build_ui(self):
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(20, 20, 20, 20)

        self.main_content = QHBoxLayout()

        # --- PANEL LEWY (Konfiguracja + Statystyki) ---
        control_panel = QVBoxLayout()
        
        control_panel.addWidget(QLabel("Driver profile"))
        self.driver_select = QComboBox()
        control_panel.addWidget(self.driver_select)

        control_panel.addWidget(QLabel("Car profile"))
        self.car_select = QComboBox()
        self.car_select.currentIndexChanged.connect(self._load_car_profile)
        control_panel.addWidget(self.car_select)

        # Informacje o aucie
        self.car_info_label = QLabel("Select car")
        self.car_info_label.setStyleSheet("color: #ecf0f1; font-size: 13px; background: #2c3e50; padding: 10px; border-radius: 5px;")
        self.car_info_label.setWordWrap(True)
        control_panel.addWidget(self.car_info_label)
        
        control_panel.addSpacing(15)

        # PANEL STATYSTYK (Tutaj przeniesione z góry)
        self.stats_group = QVBoxLayout()
        self.avg_speed_lbl = QLabel("AVG SPD: 0.0 km/h")
        self.avg_fuel_lbl = QLabel("AVG FUEL: 0.0 L/h")
        self.total_wear_lbl = QLabel("WEAR: 0.000")
        
        for lbl in [self.avg_speed_lbl, self.avg_fuel_lbl, self.total_wear_lbl]:
            lbl.setStyleSheet("color: #3498db; font-family: monospace; font-size: 12px; font-weight: bold;")
            self.stats_group.addWidget(lbl)
        control_panel.addLayout(self.stats_group)

        control_panel.addStretch()
        
        self.start_button = QPushButton("START")
        self.start_button.setFixedSize(100, 100)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.toggle_engine)
        control_panel.addWidget(self.start_button, alignment=Qt.AlignCenter)
        control_panel.addStretch()

        # --- PANEL CENTRALNY (Dashboard) ---
        dashboard_layout = QVBoxLayout()
        upper_row = QHBoxLayout()
        
        self.rpm_gauge = CircularGauge("RPM", 0, 8000, redline=6500, label_formatter=lambda v: str(int(v/1000)))
        
        center_col = QVBoxLayout()
        center_col.addStretch()
        small_widgets = QHBoxLayout()
        self.temp_gauge = CircularGauge("°C", 40, 130, major_step=20, scale_font_size=13, arc_width=10)
        self.temp_gauge.setFixedSize(130, 130)
        
        fuel_layout = QVBoxLayout()
        self.fuel_val_label = QLabel("0.0")
        self.fuel_val_label.setStyleSheet("font-size: 30px; font-weight: bold; color: white; font-family: monospace;")
        fuel_layout.addWidget(self.fuel_val_label, alignment=Qt.AlignCenter)
        fuel_layout.addWidget(QLabel("L/h"), alignment=Qt.AlignCenter)
        
        small_widgets.addWidget(self.temp_gauge)
        small_widgets.addLayout(fuel_layout)
        center_col.addLayout(small_widgets)
        
        self.gear_display = GearDisplay()
        center_col.addWidget(self.gear_display, alignment=Qt.AlignCenter)
        center_col.addStretch()

        self.speed_gauge = CircularGauge("km/h", 0, 240, major_step=20)
        
        # --- Gas Panel (Throttle) ---
        gas_col = QVBoxLayout()
        self.throttle_label = QLabel("GAS\n0%")
        # Updated font style and color for GAS label
        self.throttle_label.setStyleSheet("color: #00ff00; font-family: monospace; font-weight: bold; font-size: 14px;")
        
        self.throttle_bar = ControlBar(horizontal=False, color="#00ff00")
        self.throttle_bar.setFixedWidth(40)
        gas_col.addWidget(self.throttle_label, alignment=Qt.AlignCenter)
        gas_col.addWidget(self.throttle_bar, 1)

        upper_row.addWidget(self.rpm_gauge, 3)
        upper_row.addLayout(center_col, 2)
        upper_row.addWidget(self.speed_gauge, 3)
        upper_row.addLayout(gas_col, 0)

        # --- Brake Panel ---
        lower_row = QHBoxLayout()
        self.brake_label = QLabel("BRAKE 0%")
        # Updated font style and color for BRAKE label
        self.brake_label.setStyleSheet("color: #ff4d4d; font-family: monospace; font-weight: bold; font-size: 14px;")
        
        self.brake_bar = ControlBar(horizontal=True, color="#ff4d4d")
        self.brake_bar.setFixedHeight(30)
        lower_row.addWidget(self.brake_label)
        lower_row.addWidget(self.brake_bar, 1)

        dashboard_layout.addLayout(upper_row, 5)
        dashboard_layout.addLayout(lower_row, 1)

        self.main_content.addLayout(control_panel, 1)
        self.main_content.addLayout(dashboard_layout, 5)
        self.root.addLayout(self.main_content, 5)

        # --- KONSOLA LOGÓW ---
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMinimumHeight(200)
        self.log_console.setStyleSheet("""
            background-color: #1a1a1a; 
            color: #ffffff; 
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            border: 2px solid #333;
            padding: 5px;
        """)
        self.root.addWidget(self.log_console)

    def toggle_engine(self):
        if not self.engine_running:
            self._start_engine()
        else:
            self._stop_engine()

    def _start_engine(self):
        try:
            # Reset parametrów przed startem
            self.session_ticks = 0
            self.sum_speed = 0.0
            self.sum_fuel = 0.0
            self.sum_wear = 0.0
            self.throttle_val = 0.0
            self.throttle_bar.set_value(0)
            self.throttle_label.setText("GAS\n0%")

            sim_id = self.app_runtime.start_session(on_state_cb=self._on_simulation_state)
            self.log_signal.emit(f"--- SESSION {sim_id} STARTED ---")
            
            self.engine_running = True
            self.update_timer.start(33)
            self._apply_running_style()
            self.driver_select.setEnabled(False)
            self.car_select.setEnabled(False)
        except Exception as e:
            self.log_signal.emit(f"ERROR: {str(e)}")

    def _on_simulation_state(self, raw_state):
        m = raw_state.modules
        e = m.get("engine", {})
        v = m.get("vehicle", {})
        t = m.get("thermals", {})
        g = m.get("gearbox", {})
        w = m.get("wear", {})
        d = m.get("driver", {})

        # 1. Update Gauges
        spd = v.get("speed_kmh", 0)
        fuel = e.get("fuel_rate_lph", 0)
        wear = w.get("engine_wear", 0)
        
        self.rpm_gauge.set_value(e.get("engine_rpm", 0))
        self.speed_gauge.set_value(spd)
        self.temp_gauge.set_value(t.get("coolant_temp_c", 20))
        self.gear_display.set_gear(g.get("current_gear", 0))
        self.fuel_val_label.setText(f"{fuel:.1f}")

        # 2. Update Session Stats
        self.session_ticks += 1
        self.sum_speed += spd
        self.sum_fuel += fuel
        self.sum_wear = wear 

        self.avg_speed_lbl.setText(f"AVG SPD: {self.sum_speed/self.session_ticks:.1f} km/h")
        self.avg_fuel_lbl.setText(f"AVG FUEL: {self.sum_fuel/self.session_ticks:.2f} L/h")
        self.total_wear_lbl.setText(f"WEAR: {self.sum_wear:.5f}")

        # 3. Pełna linia logów (przywrócona)
        line = (
            f"[{raw_state.step:05d}] "
            f"RPM={e.get('engine_rpm', 0):.0f} | "
            f"SPD={spd:.1f} | "
            f"TEMP={t.get('coolant_temp_c', 0):.1f} | "
            f"FUEL={fuel:.1f} | "
            f"GEAR={g.get('current_gear', 0)} | "
            f"PEDAL={d.get('pedal', 0):.2f} "
            f"THR={d.get('throttle', 0):.2f} "
            f"RATE={d.get('throttle_rate', 0):.2f} | "
            f"WEAR={wear:.5f}"
        )
        self.log_signal.emit(line)

    def _stop_engine(self):
        self.update_timer.stop()
        self.app_runtime.stop_session()
        self.engine_running = False
        self.log_signal.emit("--- SESSION STOPPED ---")
        self._apply_off_state()
        self._apply_start_style()
        self.driver_select.setEnabled(True)
        self.car_select.setEnabled(True)

    def wheelEvent(self, event):
        """Handles mouse wheel events for gas and brake control."""
        if not self.engine_running: 
            return
            
        # Determine the change step
        step = event.angleDelta().y() / 4000.0 
        
        if event.modifiers() & Qt.ShiftModifier:
            # --- BRAKE CONTROL (Shift + Scroll) ---
            self.brake_val = max(0.0, min(1.0, self.brake_val + step))
            self.brake_bar.set_value(self.brake_val)
            self.brake_label.setText(f"BRAKE {int(self.brake_val * 100)}%")
        else:
            # --- GAS CONTROL (Regular Scroll) ---
            self.throttle_val = max(0.0, min(1.0, self.throttle_val + step))
            if self.throttle_val > 0:
                self.app_runtime.play() 
            self.throttle_bar.set_value(self.throttle_val)
            self.throttle_label.setText(f"GAS\n{int(self.throttle_val * 100)}%")

    def _load_profiles(self):
        for d in Path("simulator/profiles/drivers").glob("*.yaml"):
            self.driver_select.addItem(d.stem, str(d))
        for c in Path("simulator/profiles/cars").glob("*.yaml"):
            self.car_select.addItem(c.stem, str(c))

    def _load_car_profile(self):
        car_path = self.car_select.currentData()
        if not car_path: return
        self.car_profile = load_car_profile(car_path)
        e = self.car_profile.get("engine", {})
        v = self.car_profile.get("vehicle", {})
        self.rpm_gauge.set_range(0, e.get("max_rpm", 7000))
        self.rpm_gauge.set_redline(e.get("redline_rpm", e.get("max_rpm") * 0.9))
        info_text = (
            f"<b>Model:</b> {self.car_profile.get('name')}<br>"
            f"<b>Moc:</b> {e.get('max_power_kw')} kW<br>"
            f"<b>Moment:</b> {e.get('max_torque_nm')} Nm<br>"
            f"<b>Masa:</b> {v.get('mass_kg')} kg<br>"
            f"<b>Bak:</b> {v.get('fuel_tank_l')} L"
        )
        self.car_info_label.setText(info_text)

    def _tick(self):
        """Main simulation tick to push data to the runtime."""
        if not self.engine_running: 
            return
            
        if self.app_runtime.driver_publisher:
            self.app_runtime.driver_publisher.set_controls(self.throttle_val, self.brake_val)
                        

    @Slot(str)
    def log(self, message: str):
        self.log_console.appendPlainText(message)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    def _apply_off_state(self):
        """Resets the UI widgets to their default off state."""
        self.rpm_gauge.set_value(0)
        self.speed_gauge.set_value(0)
        self.fuel_val_label.setText("0.0")
        self.gear_display.set_gear(0)
        
        # Reset bars and labels
        self.throttle_val = 0.0
        self.throttle_bar.set_value(0)
        self.throttle_label.setText("GAS\n0%")
        
        self.brake_val = 0.0
        self.brake_bar.set_value(0)
        self.brake_label.setText("BRAKE 0%")

    def _apply_start_style(self):
        self.start_button.setText("START")
        self.start_button.setStyleSheet("background-color: #2ecc71; border-radius: 50px; color: black; font-weight: bold;")

    def _apply_running_style(self):
        self.start_button.setText("STOP")
        self.start_button.setStyleSheet("background-color: #e74c3c; border-radius: 50px; color: white; font-weight: bold;")