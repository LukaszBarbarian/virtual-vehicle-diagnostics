from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QPlainTextEdit
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot

from app.app_config import AppConfig
from app.runtimes.runtime import ApplicationRuntime
from ml.datasets.feature_config import SIM_DT, WINDOW_ROWS
from ml.inference.inference_processor import AIInferenceEngine
from ui2.profile_loader import load_car_profile
from ui2.widgets.coaching_panel import CoachingPanel
from ui2.widgets.control_bar import ControlBar
from ui2.widgets.gauge import CircularGauge
from ui2.widgets.gear_display import GearDisplay


class MainWindow(QWidget):
    """
    Main application window that integrates the dashboard UI, telemetry processing, and AI coaching.
    """
    log_signal = Signal(str)
    coaching_update_signal = Signal(float, str, str)
    # Simulation ticks arrive on the physics thread; signals hand them to the Qt GUI thread
    state_signal = Signal(object)
    sim_error_signal = Signal()

    def __init__(self):
        """
        Initializes the main window, sets up simulation engines, and triggers UI construction.
        """
        super().__init__()
        self.setWindowTitle("Vehicle Simulator Pro")
        self.setFixedSize(1150, 800)

        self.engine_running = False
        self.car_profile = None
        self.session_ticks = 0
        self.sum_speed = 0.0
        self.sum_fuel = 0.0
        self.sum_wear = 0.0

        self.driving_score = 100.0
        self.current_display = 0.0
        self.throttle_val = 0.0
        self.brake_val = 0.0

        self.ai_engine = None
        self.ai_error = None
        try:
            self.ai_engine = AIInferenceEngine()
        except Exception as e:
            # No trained model yet: the cockpit still runs, only the AI coach is disabled
            self.ai_error = str(e)

        self.app_runtime = ApplicationRuntime(AppConfig.KAFKA_BROKERS)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._tick)
        self.log_signal.connect(self.log)
        self.state_signal.connect(self._on_simulation_state)
        self.sim_error_signal.connect(self._on_simulation_error)

        self._build_ui()
        self._load_profiles()
        self._apply_off_state()
        self._apply_start_style()

        self.coaching_update_signal.connect(self.coaching_panel.update_coaching)

        if self.ai_engine is None:
            self.log(f"AI coach disabled - no model at {AppConfig.MODEL_URI}. Train one with run_ml_datasets.py.")
            self.coaching_panel.update_coaching(0.0, "neutral", "AI model not trained yet")
        if self.app_runtime.spark_error:
            self.log("Spark Bronze ingestion not running - telemetry is streamed to Kafka only.")

    def _build_ui(self):
        """
        Constructs the complex layout including control panels, dashboard gauges, and the log console.
        """
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(20, 20, 20, 20)

        self.main_content = QHBoxLayout()

        control_panel = QVBoxLayout()
        control_panel.addWidget(QLabel("Driver profile"))
        self.driver_select = QComboBox()
        control_panel.addWidget(self.driver_select)

        control_panel.addWidget(QLabel("Car profile"))
        self.car_select = QComboBox()
        self.car_select.currentIndexChanged.connect(self._load_car_profile)
        control_panel.addWidget(self.car_select)

        self.car_info_label = QLabel("Select car")
        self.car_info_label.setStyleSheet("color: #ecf0f1; font-size: 13px; background: #2c3e50; padding: 10px; border-radius: 5px;")
        self.car_info_label.setWordWrap(True)
        control_panel.addWidget(self.car_info_label)

        control_panel.addSpacing(15)

        self.stats_group = QVBoxLayout()
        self.avg_speed_lbl = QLabel("AVG SPD: 0.0 km/h")
        self.avg_fuel_lbl = QLabel("AVG FUEL: 0.0 L/h")
        self.total_wear_lbl = QLabel("WEAR: 0.000")

        for lbl in [self.avg_speed_lbl, self.avg_fuel_lbl, self.total_wear_lbl]:
            lbl.setStyleSheet("color: #3498db; font-family: monospace; font-size: 12px; font-weight: bold;")
            self.stats_group.addWidget(lbl)
        control_panel.addLayout(self.stats_group)

        control_panel.addSpacing(20)

        self.coaching_panel = CoachingPanel()
        control_panel.addWidget(self.coaching_panel)
        control_panel.addStretch()

        self.start_button = QPushButton("START")
        self.start_button.setFixedSize(100, 100)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.toggle_engine)
        control_panel.addWidget(self.start_button, alignment=Qt.AlignCenter)
        control_panel.addStretch()

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

        gas_col = QVBoxLayout()
        self.throttle_label = QLabel("GAS\n0%")
        self.throttle_label.setStyleSheet("color: #00ff00; font-family: monospace; font-weight: bold; font-size: 14px;")

        self.throttle_bar = ControlBar(horizontal=False, color="#00ff00")
        self.throttle_bar.setFixedWidth(40)
        gas_col.addWidget(self.throttle_label, alignment=Qt.AlignCenter)
        gas_col.addWidget(self.throttle_bar, 1)

        upper_row.addWidget(self.rpm_gauge, 3)
        upper_row.addLayout(center_col, 2)
        upper_row.addWidget(self.speed_gauge, 3)
        upper_row.addLayout(gas_col, 0)

        lower_row = QHBoxLayout()
        self.brake_label = QLabel("BRAKE 0%")
        self.brake_label.setStyleSheet("color: #ff4d4d; font-family: monospace; font-weight: bold; font-size: 14px;")

        self.brake_bar = ControlBar(horizontal=True, color="#ff4d4d")
        self.brake_bar.setFixedHeight(30)
        lower_row.addWidget(self.brake_label)
        lower_row.addWidget(self.brake_bar, 1)

        dashboard_layout.addLayout(upper_row, 5)
        dashboard_layout.addLayout(lower_row, 1)

        self.main_content.addLayout(control_panel, 1)
        self.main_content.addLayout(dashboard_layout, 4)
        self.root.addLayout(self.main_content, 5)

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
        """
        Switches the simulation state between running and stopped.
        """
        if not self.engine_running:
            self._start_engine()
        else:
            self._stop_engine()

    def _start_engine(self):
        """
        Resets session data, initializes the simulation runtime, and starts the UI update timer.
        """
        try:
            self.session_ticks = 0
            self.sum_speed = 0.0
            self.sum_fuel = 0.0
            self.sum_wear = 0.0
            self.throttle_val = 0.0
            self.brake_val = 0.0
            self.throttle_bar.set_value(0)
            self.brake_bar.set_value(0)
            self.throttle_label.setText("GAS\n0%")

            if self.ai_engine:
                self.ai_engine.reset()

            sim_id = self.app_runtime.start_session(
                on_state_cb=self.state_signal.emit,
                car_profile_path=self.car_select.currentData(),
                driver_profile_path=self.driver_select.currentData(),
                on_error=self.sim_error_signal.emit,
            )
            self.log_signal.emit(f"--- SESSION {sim_id} STARTED ---")

            self.engine_running = True
            self.update_timer.start(33)
            self._apply_running_style()
            self.driver_select.setEnabled(False)
            self.car_select.setEnabled(False)
        except Exception as e:
            self.log_signal.emit(f"ERROR: {str(e)}")

    @Slot(object)
    def _on_simulation_state(self, raw_state):
        """
        Processes incoming telemetry data, updates gauges, and runs AI inference for driver coaching.
        Runs on the GUI thread (connected through state_signal).
        """
        m = raw_state.modules
        e, v, t, g, w, d = [m.get(k, {}) for k in ["engine", "vehicle", "thermals", "gearbox", "wear", "driver"]]

        curr_rpm = e.get("engine_rpm", 0.0)
        curr_spd = v.get("speed_kmh", 0.0)
        curr_temp = t.get("coolant_temp_c", 0.0)
        curr_fuel = e.get("fuel_rate_lph", 0.0)
        curr_wear = w.get("engine_wear", 0.0)
        curr_throttle = d.get("throttle", 0.0)
        curr_gear = g.get("current_gear", 0)
        curr_load = v.get("load", 0.0)

        self.rpm_gauge.set_value(curr_rpm)
        self.speed_gauge.set_value(curr_spd)
        self.temp_gauge.set_value(curr_temp)
        self.gear_display.set_gear(curr_gear)
        self.fuel_val_label.setText(f"{curr_fuel:.1f}")

        self.session_ticks += 1
        self.sum_speed += curr_spd
        self.sum_fuel += curr_fuel

        self.avg_speed_lbl.setText(f"AVG SPD: {self.sum_speed / self.session_ticks:.1f} km/h")
        self.avg_fuel_lbl.setText(f"AVG FUEL: {self.sum_fuel / self.session_ticks:.2f} L/h")
        self.total_wear_lbl.setText(f"WEAR: {curr_wear:.5f}")

        if self.ai_engine is None:
            return

        # Same signals as the Silver/Gold layers, so live features match the training data
        self.ai_engine.add_sample(
            rpm=curr_rpm,
            throttle=curr_throttle,
            load=curr_load,
            speed=curr_spd,
            gear=curr_gear,
            engine_wear=curr_wear,
        )

        if raw_state.step % 10 == 0:
            try:
                prediction = self.ai_engine.get_prediction()
                if prediction:
                    agg_score = prediction["score"]
                    label = prediction["label"]
                    wear_delta = self.ai_engine.observed_wear_delta()
                    self.current_display = (0.7 * self.current_display + 0.3 * agg_score)

                    if raw_state.step % 30 == 0:
                        self.log_signal.emit(
                            f"[AI] {label} | P(aggressive): {agg_score:.1f}% | wear last 10 s: {wear_delta:.2e}"
                        )

                    if agg_score > 70:
                        style_key = "aggressive"
                        status_name = "DANGER"
                    elif agg_score > 30:
                        style_key = "normal"
                        status_name = "CAUTION"
                    else:
                        style_key = "calm"
                        status_name = "OPTIMAL"

                    display_text = (
                        f"STATUS: {status_name}\n"
                        f"P(AGGRESSIVE): {int(agg_score)}%\n"
                        f"WEAR 10s: {wear_delta:.2e}"
                    )

                    self.coaching_update_signal.emit(
                        float(self.current_display),
                        style_key,
                        display_text
                    )
                else:
                    progress_val = len(self.ai_engine.buffer)
                    progress_pct = self.ai_engine.warmup_progress * 100

                    if raw_state.step % 30 == 0:
                        self.log_signal.emit(f"AI warming up: {progress_pct:.0f}% ({progress_val}/{WINDOW_ROWS} samples)")

                    self.coaching_update_signal.emit(
                        0.0,
                        "neutral",
                        f"AI is warming up...\nProgress: {progress_pct:.0f}%"
                    )
            except Exception as e:
                self.log_signal.emit(f"AI UI ERROR: {e}")

    @Slot()
    def _on_simulation_error(self):
        """
        Stops the session when the physics thread fails (most often: Kafka is not reachable).
        """
        self.log(f"Simulation stopped after an error - is Kafka running at {AppConfig.KAFKA_BROKERS}? See the console for details.")
        if self.engine_running:
            self._stop_engine()

    def _stop_engine(self):
        """
        Shuts down the simulation runtime, stops timers, and resets the UI to the off state.
        """
        self.update_timer.stop()
        self.app_runtime.stop_session()
        self.engine_running = False
        self.log_signal.emit("--- SESSION STOPPED ---")
        self._apply_off_state()
        self._apply_start_style()
        self.driver_select.setEnabled(True)
        self.car_select.setEnabled(True)

    def wheelEvent(self, event):
        """
        Maps mouse wheel interaction to throttle and brake control based on modifier keys.
        """
        if not self.engine_running:
            return

        step = event.angleDelta().y() / 4000.0

        if event.modifiers() & Qt.ShiftModifier:
            self.brake_val = max(0.0, min(1.0, self.brake_val + step))
            self.brake_bar.set_value(self.brake_val)
            self.brake_label.setText(f"BRAKE {int(self.brake_val * 100)}%")
        else:
            self.throttle_val = max(0.0, min(1.0, self.throttle_val + step))
            if self.throttle_val > 0:
                self.app_runtime.play(SIM_DT)
            self.throttle_bar.set_value(self.throttle_val)
            self.throttle_label.setText(f"GAS\n{int(self.throttle_val * 100)}%")

    def _load_profiles(self):
        """
        Scans the local filesystem for driver and car YAML profiles and populates selection combos.
        """
        for d in sorted((AppConfig.MAIN_PROFILES_PATH / "drivers").glob("*.yaml")):
            self.driver_select.addItem(d.stem, str(d))
        for c in sorted((AppConfig.MAIN_PROFILES_PATH / "cars").glob("*.yaml")):
            self.car_select.addItem(c.stem, str(c))

    def _load_car_profile(self):
        """
        Loads the selected car's technical specifications and updates the gauge ranges accordingly.
        """
        car_path = self.car_select.currentData()
        if not car_path: return
        self.car_profile = load_car_profile(car_path)
        e = self.car_profile.get("engine", {})
        v = self.car_profile.get("vehicle", {})
        g = self.car_profile.get("gearbox", {})
        limits = self.car_profile.get("limits", {})
        display = self.car_profile.get("display", {})
        max_rpm = e.get("max_rpm", 7000)
        self.rpm_gauge.set_range(0, max_rpm)
        self.rpm_gauge.set_redline(limits.get("redline_rpm", max_rpm * 0.9))
        self.speed_gauge.set_range(0, display.get("max_speed_on_gauge", 240))
        info_text = (
            f"<b>Model:</b> {self.car_profile.get('name')}<br>"
            f"<b>Power:</b> {e.get('max_power_kw')} kW<br>"
            f"<b>Torque:</b> {e.get('base_torque_nm')} Nm<br>"
            f"<b>Weight:</b> {v.get('mass_kg')} kg<br>"
            f"<b>Gears:</b> {len(g.get('gears', []))}"
        )
        self.car_info_label.setText(info_text)

    def _tick(self):
        """
        Regularly pushes current driver inputs (throttle/brake) to the simulation runtime.
        """
        if not self.engine_running:
            return
        if self.app_runtime.driver_publisher:
            self.app_runtime.driver_publisher.set_controls(self.throttle_val, self.brake_val)

    @Slot(str)
    def log(self, message: str):
        """
        Appends a message to the UI log console and automatically scrolls to the bottom.
        """
        self.log_console.appendPlainText(message)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    def _apply_off_state(self):
        """
        Resets all interactive dashboard widgets to their zero/neutral positions.
        """
        self.rpm_gauge.set_value(0)
        self.speed_gauge.set_value(0)
        self.fuel_val_label.setText("0.0")
        self.gear_display.set_gear(0)
        self.throttle_val = 0.0
        self.throttle_bar.set_value(0)
        self.throttle_label.setText("GAS\n0%")
        self.brake_val = 0.0
        self.brake_bar.set_value(0)
        self.brake_label.setText("BRAKE 0%")

    def _apply_start_style(self):
        """
        Styles the engine button for the 'ready to start' state.
        """
        self.start_button.setText("START")
        self.start_button.setStyleSheet("background-color: #2ecc71; border-radius: 50px; color: black; font-weight: bold;")

    def _apply_running_style(self):
        """
        Styles the engine button for the 'currently running' state.
        """
        self.start_button.setText("STOP")
        self.start_button.setStyleSheet("background-color: #e74c3c; border-radius: 50px; color: white; font-weight: bold;")