import threading
from collections import deque
from typing import Dict, Any, Optional
import time

from streaming.kafka.consumers.base import EventHandler


class DashboardStateHandler(EventHandler):
    """
    Trzyma:
    - ostatni znany stan
    - historię RPM + Gear do wykresu
    """

    def __init__(self, history_size: int = 300):
        self._lock = threading.Lock()
        self._latest_state: Optional[Dict[str, Any]] = None

        # historia do wykresu (np. ~60s przy 5Hz)
        self._history = deque(maxlen=history_size)

    def handle(self, event: Dict[str, Any]) -> None:
        if event.get("event_type") != "simulation.raw":
            return

        payload = event.get("payload")
        if not payload:
            return

        with self._lock:
            self._latest_state = payload

            engine = payload["modules"]["engine"]
            gearbox = payload["modules"]["gearbox"]
            vehicle = payload["modules"]["vehicle"]

            self._history.append({
                "t": payload.get("time", time.time()),
                "rpm": engine.get("engine_rpm", 0.0),
                "gear": gearbox.get("current_gear", 0),
                "speed_kmh": vehicle.get("speed_kmh", 0)
            })

    def get_latest_state(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._latest_state

    def get_history(self):
        with self._lock:
            return list(self._history)
