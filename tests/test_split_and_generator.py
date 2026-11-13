import random

from app.app_config import AppConfig
from app.runtimes.generate_sessions import run_session
from ml.datasets.feature_config import split_simulation_ids


class CollectingKafka:
    """Kafka stand-in that keeps every published event."""

    def __init__(self):
        self.events = []

    def send(self, topic, payload):
        self.events.append(payload)

    def producer(self):
        return self

    def flush(self):
        pass


def test_split_is_deterministic_disjoint_and_complete():
    ids = [f"id-{i:02d}" for i in range(10)]
    train, test = split_simulation_ids(reversed(ids))

    assert (train, test) == split_simulation_ids(ids)
    assert train.isdisjoint(test)
    assert train | test == set(ids)
    assert len(test) == 2


def test_single_session_is_used_for_both_sets():
    assert split_simulation_ids(["only"]) == ({"only"}, {"only"})


def test_generator_is_reproducible_and_injects_glitches():
    car = AppConfig.DEFAULT_CAR_PROFILE

    def generate(glitch_rate):
        kafka = CollectingKafka()
        sim_id = run_session(kafka, car, "sport", 0.5, random.Random(7), glitch_rate, random.Random(8))
        return sim_id, kafka.events

    sim_a, clean_a = generate(0.0)
    sim_b, clean_b = generate(0.0)
    assert sim_a == sim_b
    assert [e["payload"]["modules"]["vehicle"]["speed_kmh"] for e in clean_a] == \
           [e["payload"]["modules"]["vehicle"]["speed_kmh"] for e in clean_b]

    _, glitched = generate(0.05)
    bad = [e for e in glitched
           if e["payload"]["modules"]["engine"]["engine_rpm"] > 10000
           or e["payload"]["modules"]["vehicle"]["speed_kmh"] is None]
    assert 0 < len(bad) < len(glitched) * 0.15
