# ui/bootstrap.py
from simulator.core.loader.car_profile import CarProfileLoader
from simulator.core.loader.driver_profile import DriverProfileLoader
from simulator.core.loader.environment_profile import EnvironmentLoader
from simulator.core.loader.wear_profile import WearProfileLoader
from simulator.core.simulation.simulation import Simulation

MAIN_PROFILES_PATH = "simulator/profiles"

def bootstrap_simulation():
    car_spec = CarProfileLoader.load(f"{MAIN_PROFILES_PATH}/cars/ford_focus.yaml")
    driver_spec = DriverProfileLoader.load(f"{MAIN_PROFILES_PATH}/drivers/normal.yaml")
    wear_spec = WearProfileLoader.load(f"{MAIN_PROFILES_PATH}/worlds/realistic_wear.yaml")
    env_spec = EnvironmentLoader.load(f"{MAIN_PROFILES_PATH}/worlds/summer.yaml")

    sim = Simulation(
        car_spec,
        driver_spec,
        wear_spec,
        env_spec
    )

    return sim
