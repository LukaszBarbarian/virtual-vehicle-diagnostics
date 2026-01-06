import os
import sys
from simulator.core.loader.car_profile import CarProfileLoader
from simulator.core.loader.driver_profile import DriverProfileLoader
from simulator.core.loader.environment_profile import EnvironmentLoader
from simulator.core.loader.wear_profile import WearProfileLoader
from simulator.core.simulation.simulation import Simulation
from simulator.core.simulation.simulation_engine import SimulationEngine
from simulator.services.driver_service import DriverKafkaListener, DriverService
from streaming.event_builder import EventBuilder
from streaming.kafka_collector import KafkaCollector
from streaming.kafka_service import KafkaService

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAIN_PROFILES_PATH = "simulator/profiles"


def main():
    car_spec   = CarProfileLoader.load(f"{MAIN_PROFILES_PATH}/cars/ford_focus.yaml")
    driver_spec = DriverProfileLoader.load(f"{MAIN_PROFILES_PATH}/drivers/normal.yaml")
    wear_spec   = WearProfileLoader.load(f"{MAIN_PROFILES_PATH}/worlds/realistic_wear.yaml")
    env_spec    = EnvironmentLoader.load(f"{MAIN_PROFILES_PATH}/worlds/summer.yaml")

    sim = Simulation(car_spec,
                    driver_spec, 
                    wear_spec, 
                    env_spec)
    


     # ---------- KAFKA OUT (STATE) ----------
    kafka = KafkaService("localhost:9092")
    collector = KafkaCollector(kafka)
    EventBuilder(sim.state_bus, collector)

    # ---------- DRIVER SERVICE + KAFKA IN ----------
    driver_service = DriverService(sim.driver)
    driver_listener = DriverKafkaListener(kafka, driver_service)
    driver_listener.start()

    sim_engine = SimulationEngine(sim)
    sim_engine.start(0.1)




if __name__ == "__main__":
    main()