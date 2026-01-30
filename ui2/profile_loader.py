import yaml
from pathlib import Path

def load_car_profile(path: str) -> dict:
    """
    Reads a vehicle configuration from a YAML file and returns it as a dictionary.
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)