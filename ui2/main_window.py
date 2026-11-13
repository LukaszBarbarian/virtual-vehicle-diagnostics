import math

from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot

from app.app_config import AppConfig
from app.runtimes.runtime import ApplicationRuntime
from ml.datasets.feature_config import SIM_DT, WINDOW_ROWS
from ml.inference.inference_processor import AIInferenceEngine
from ui2.profile_loader import load_car_profile
from ui2.theme import COLORS, START_STYLE, STOP_STYLE, STYLESHEET
from ui2.widgets.coaching_panel import CoachingPanel
from ui2.widgets.control_bar import ControlBar
from ui2.widgets.gauge import CircularGauge
from ui2.widgets.gear_display import GearDisplay


def card() -> QFrame:
    frame = QFrame()
    frame.setObjectName("card")
    return frame


def section(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("sectionLabel")
    return label


def oil_color(temp_c: float) -> str:
    """Cold engine and overheating both wear the engine: show them in the gauge."""
    if temp_c < 60:
        return "cold"
    if temp_c > 120:
        return "critical"
    return "good"


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
        self.setWindowTitle("Vehicle Diagnostics · Cockpit")
        self.setFixedSize(1320, 800)
        self.setStyleSheet(STYLESHEET)

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
            self.coaching_panel.update_coaching(0.0, "neutral", "No trained model yet: run run_ml_datasets.py")
        if self.app_runtime.spark_error:
            self.log("Spark Bronze ingestion not running - telemetry is streamed to Kafka only.")

    # ------------------------------------------------------------------ layout

    def _build_ui(self):
        """
        Sidebar (profiles, car specs, session stats, start button) next to the instrument cluster,
        the AI coach and the event log.
        """
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        root.addWidget(self._build_sidebar())

        main = QVBoxLayout()
        main.setSpacing(16)
        main.addWidget(self._build_cluster(), 5)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)
        self.coaching_panel = CoachingPanel()
        bottom.addWidget(self.coaching_panel, 3)
        bottom.addWidget(self._build_log(), 2)
        main.addLayout(bottom, 2)

        root.addLayout(main, 1)

    def _build_sidebar(self) -> QFrame:
        side = card()
        side.setFixedWidth(290)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(8)

        title = QLabel("Vehicle Diagnostics")
        title.setObjectName("appTitle")
        lay.addWidget(title)
        subtitle = QLabel("Live cockpit  ·  Kafka  ·  AI coach")
        subtitle.setObjectName("appSubtitle")
        lay.addWidget(subtitle)
        lay.addSpacing(14)

        lay.addWidget(section("Car"))
        self.car_select = QComboBox()
        self.car_select.currentIndexChanged.connect(self._load_car_profile)
        lay.addWidget(self.car_select)

        self.car_info_label = QLabel("")
        self.car_info_label.setObjectName("carName")
        self.car_info_label.setVisible(False)  # the car name is shown in the selector
        self.car_info_label.setWordWrap(True)
        lay.addWidget(self.car_info_label)

        self.spec_chips = [QLabel() for _ in range(4)]
        chips = QGridLayout()
        chips.setHorizontalSpacing(6)
        chips.setVerticalSpacing(6)
        for i, chip in enumerate(self.spec_chips):
            chip.setObjectName("chip")
            chip.setAlignment(Qt.AlignCenter)
            chips.addWidget(chip, i // 2, i % 2)
        lay.addLayout(chips)
        lay.addSpacing(10)

        lay.addWidget(section("Driver profile"))
        self.driver_select = QComboBox()
        lay.addWidget(self.driver_select)
        lay.addSpacing(16)

        lay.addWidget(section("This session"))
        stats = QGridLayout()
        stats.setVerticalSpacing(10)
        self.avg_speed_lbl, self.avg_fuel_lbl, self.total_wear_lbl = QLabel(), QLabel(), QLabel()
        for row, (name, value) in enumerate([
            ("Average speed", self.avg_speed_lbl),
            ("Average fuel", self.avg_fuel_lbl),
            ("Engine wear", self.total_wear_lbl),
        ]):
            label = QLabel(name)
            label.setObjectName("statLabel")
            value.setObjectName("statValue")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            stats.addWidget(label, row, 0)
            stats.addWidget(value, row, 1)
        lay.addLayout(stats)

        lay.addStretch()
        hint = QLabel("Scroll  →  throttle\nShift + scroll  →  brake")
        hint.setObjectName("appSubtitle")
        hint.setAlignment(Qt.AlignCenter)
        lay.addWidget(hint)
        lay.addSpacing(8)

        self.start_button = QPushButton("START ENGINE")
        self.start_button.setObjectName("startButton")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.toggle_engine)
        lay.addWidget(self.start_button)
        return side

    def _build_cluster(self) -> QFrame:
        cluster = card()
        lay = QHBoxLayout(cluster)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        self.rpm_gauge = CircularGauge(
            "Engine", 0, 8000, redline=6500, unit="RPM",
            label_formatter=lambda v: f"{v / 1000:.0f}", value_formatter=lambda v: f"{v:,.0f}".replace(",", " "),
        )
        lay.addWidget(self.rpm_gauge, 3)

        center = QVBoxLayout()
        center.setSpacing(10)
        center.addStretch()
        self.temp_gauge = CircularGauge(
            "Oil", 0, 180, major_step=60, unit="°C", scale_font_size=7, arc_width=14,
            color_for_value=oil_color,
        )
        self.temp_gauge.setFixedSize(160, 160)
        center.addWidget(self.temp_gauge, alignment=Qt.AlignCenter)
        self.gear_display = GearDisplay()
        center.addWidget(self.gear_display, alignment=Qt.AlignCenter)

        fuel = QVBoxLayout()
        fuel.setSpacing(0)
        self.fuel_val_label = QLabel("0.0")
        self.fuel_val_label.setObjectName("statValue")
        self.fuel_val_label.setAlignment(Qt.AlignCenter)
        fuel_unit = QLabel("L/h fuel")
        fuel_unit.setObjectName("statLabel")
        fuel_unit.setAlignment(Qt.AlignCenter)
        fuel.addWidget(self.fuel_val_label)
        fuel.addWidget(fuel_unit)
        center.addLayout(fuel)
        center.addStretch()
        lay.addLayout(center, 2)

        self.speed_gauge = CircularGauge(
            "Speed", 0, 240, major_step=40, unit="km/h",
        )
        lay.addWidget(self.speed_gauge, 3)

        pedals = QHBoxLayout()
        pedals.setSpacing(4)
        self.throttle_bar = ControlBar(color=COLORS["throttle"], caption="THROTTLE")
        self.brake_bar = ControlBar(color=COLORS["brake"], caption="BRAKE")
        for bar in (self.throttle_bar, self.brake_bar):
            bar.setFixedWidth(58)
            pedals.addWidget(bar)
        lay.addLayout(pedals)
        return cluster

    def _build_log(self) -> QFrame:
        box = card()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(18, 14, 12, 12)
        lay.setSpacing(6)
        lay.addWidget(section("Event log"))
        self.log_console = QPlainTextEdit()
        self.log_console.setObjectName("log")
        self.log_console.setReadOnly(True)
        lay.addWidget(self.log_console)
        return box

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

            if self.ai_engine:
                self.ai_engine.reset()
                self.coaching_panel.reset()

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
        self.temp_gauge.set_value(t.get("oil_temp_c", curr_temp))
        self.gear_display.set_gear(curr_gear)
        self.fuel_val_label.setText(f"{curr_fuel:.1f}")

        self.session_ticks += 1
        self.sum_speed += curr_spd
        self.sum_fuel += curr_fuel

        self.avg_speed_lbl.setText(f"{self.sum_speed / self.session_ticks:.0f} km/h")
        self.avg_fuel_lbl.setText(f"{self.sum_fuel / self.session_ticks:.1f} L/h")
        self.total_wear_lbl.setText(f"{curr_wear * 100:.2f} %")

        if self.ai_engine is None:
            return

        # Same signals as the Silver/Gold layers, so live features match the training data
        self.ai_engine.add_sample(
            rpm=curr_rpm,
            throttle=curr_throttle,
            load=curr_load,
            speed=curr_spd,
            gear=curr_gear,
            oil_temp=t.get("oil_temp_c", 0.0),
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
                            f"AI  {'HIGH WEAR' if label == 'AGGRESSIVE' else 'normal':<9}  "
                            f"P {agg_score:5.1f}%  ·  wear 10 s {wear_delta * 100:.3f}%"
                        )

                    oil = t.get("oil_temp_c", 0.0)
                    if agg_score > 70:
                        style_key = "aggressive"
                        advice = ("Engine is overheating: lift off and let it cool" if oil > 120
                                  else "Cold engine under heavy load: go easy until it warms up" if oil < 60
                                  else "Heavy load and high revs: ease off the throttle")
                    elif agg_score > 30:
                        style_key = "normal"
                        advice = "Wear is rising: smoother throttle keeps the engine healthy"
                    else:
                        style_key = "calm"
                        advice = "Smooth driving: engine wear is normal"

                    display_text = f"{advice}\nMeasured wear, last 10 s: {wear_delta * 100:.3f} %"

                    self.coaching_update_signal.emit(
                        float(self.current_display),
                        style_key,
                        display_text
                    )
                else:
                    progress_val = len(self.ai_engine.buffer)
                    progress_pct = self.ai_engine.warmup_progress * 100

                    if raw_state.step % 30 == 0:
                        self.log_signal.emit(f"AI  warming up {progress_pct:.0f}%  ({progress_val}/{WINDOW_ROWS} ticks)")

                    self.coaching_update_signal.emit(
                        0.0,
                        "neutral",
                        f"Collecting the first 10 seconds of driving: {progress_pct:.0f}%"
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
        else:
            self.throttle_val = max(0.0, min(1.0, self.throttle_val + step))
            if self.throttle_val > 0:
                self.app_runtime.play(SIM_DT)
            self.throttle_bar.set_value(self.throttle_val)

    def _load_profiles(self):
        """
        Scans the local filesystem for driver and car YAML profiles and populates selection combos.
        """
        for d in sorted((AppConfig.MAIN_PROFILES_PATH / "drivers").glob("*.yaml")):
            self.driver_select.addItem(d.stem.capitalize(), str(d))
        for c in sorted((AppConfig.MAIN_PROFILES_PATH / "cars").glob("*.yaml")):
            self.car_select.addItem(load_car_profile(str(c)).get("name", c.stem), str(c))

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
        # Like a real tachometer: the scale runs past the cut-off, the red zone starts at the redline
        self.rpm_gauge.set_range(0, math.ceil((max_rpm + 500) / 1000) * 1000)
        self.rpm_gauge.set_redline(limits.get("redline_rpm", max_rpm * 0.95))
        self.speed_gauge.set_range(0, display.get("max_speed_on_gauge", 240))
        self.car_info_label.setText("")
        specs = [
            f"{e.get('max_power_kw')} kW",
            f"{e.get('base_torque_nm')} Nm",
            f"{v.get('mass_kg')} kg",
            f"{len(g.get('gears', []))} gears",
        ]
        for chip, text in zip(self.spec_chips, specs):
            chip.setText(text)

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
        self.temp_gauge.set_value(0)
        self.fuel_val_label.setText("0.0")
        self.gear_display.set_gear(0)
        self.throttle_val = 0.0
        self.throttle_bar.set_value(0)
        self.brake_val = 0.0
        self.brake_bar.set_value(0)
        for label in (self.avg_speed_lbl, self.avg_fuel_lbl, self.total_wear_lbl):
            label.setText("–")

    def _apply_start_style(self):
        """
        Styles the engine button for the 'ready to start' state.
        """
        self.start_button.setText("START ENGINE")
        self.start_button.setStyleSheet(START_STYLE)

    def _apply_running_style(self):
        """
        Styles the engine button for the 'currently running' state.
        """
        self.start_button.setText("STOP ENGINE")
        self.start_button.setStyleSheet(STOP_STYLE)
