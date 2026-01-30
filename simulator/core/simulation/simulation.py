# simulation.py
from simulator.core.builder.car_builder import CarBuilder
from simulator.core.builder.driver_builder import DriverBuilder
from simulator.core.builder.wear_builder import WearBuilder
from simulator.core.models.model_specification import (
    CarSpecification,
    DriverSpecification,
    EnvironmentSpecification,
    WearSpecification
)
from simulator.core.state.raw_state import RawSimulationState
from simulator.core.state.state_bus import StateBus
from simulator.modules.driver import DriverInput, DriverModule
from simulator.modules.engine import EngineInput, EngineModule
from simulator.modules.gearbox import GearboxInput, GearboxModule
from simulator.modules.thermals import ThermalInput, ThermalModule
from simulator.modules.vehicle import VehicleInput, VehicleModule
from simulator.modules.wear import WearInput, WearModule
import uuid

class Simulation:
    """
    The central orchestrator of the vehicle simulation, managing data flow between all mechanical and driver modules.
    """
    def __init__(
        self,
        car_spec: CarSpecification,
        driver_spec: DriverSpecification,
        wear_spec: WearSpecification,
        env_spec: EnvironmentSpecification
    ):
        """
        Initializes the simulation by building all necessary modules and setting up the initial state.
        """
        self.simulation_id = str(uuid.uuid4()) 
        self.car = CarBuilder.build(car_spec)
        self.env = env_spec
        self.driver = DriverBuilder.build(driver_spec)
        self.wear = WearBuilder.build(wear_spec)
        self.init()

    def init(self):
        """
        Triggers the initialization sequence for time tracking and communication buses.
        """
        self.init_state()

    def init_state(self):
        """
        Resets simulation counters and initializes the internal StateBus for event distribution.
        """
        self.time = 0.0
        self.step_count = 0
        self.state_bus = StateBus()

    def update_modules(self, dt: float, engine: EngineModule, gearbox: GearboxModule,
                       vehicle: VehicleModule, thermals: ThermalModule,
                       wear: WearModule, driver: DriverModule):
        """
        Handles the sequential dependency chain of the simulation physics, updating each module's input and state.
        """
        driver.input = DriverInput(
            engine_rpm=engine.state.engine_rpm,
            max_rpm=engine.spec.max_rpm,
        )
        driver.update(dt)

        gearbox.input = GearboxInput(
            engine_rpm=engine.state.engine_rpm,
            throttle=driver.output.throttle,
            vehicle_speed=vehicle.state.speed_kmh,
            throttle_rate=driver.output.throttle_rate
        )
        gearbox.update(dt)

        wear.input = WearInput(
            engine_temp_c=thermals.state.coolant_temp_c,
            oil_temp_c=thermals.state.oil_temp_c,
            load=vehicle.state.load,
            engine_rpm=engine.state.engine_rpm,
            gearbox_temp_c=gearbox.state.gearbox_temp_c,
            throttle_rate=driver.state.throttle_rate
        )
        wear.update(dt)

        engine.input = EngineInput(
            throttle=driver.output.throttle,
            current_gear=gearbox.state.current_gear,
            vehicle_speed=vehicle.state.speed_kmh,
            ambient_temp_c=self.env.ambient_temp,
            cooling_efficiency=wear.output.cooling_efficiency,
            torque_loss_factor=wear.output.torque_loss_factor,
            clutch_factor=0.0 if gearbox.state.shift_event else 1.0,
            gear_ratio_total=gearbox.output.gear_ratio,
            wheel_radius_m=vehicle.wheel_radius,
            vehicle_acc_mps2=vehicle.state.acc_mps2,
            vehicle_mass_kg=vehicle.state.mass_kg
        )
        engine.update(dt)

        vehicle.input = VehicleInput(
            torque_nm=engine.output.torque_nm,
            gear_ratio=gearbox.output.gear_ratio,
            brake=driver.output.brake,
            cargo_mass_kg=driver.output.cargo_mass_kg,
            road_incline_pct=self.env.road_incline
        )
        vehicle.update(dt)

        thermals.input = ThermalInput(
            heat_kw=engine.output.heat_kw,
            vehicle_speed=vehicle.state.speed_kmh,
            ambient_temp_c=self.env.ambient_temp,
            cooling_efficiency=wear.output.cooling_efficiency
        )
        thermals.update(dt)

    def step(self, dt: float):
        """
        Executes a single simulation step, captures the current state snapshot, and triggers a broadcast.
        """
        if dt <= 0.0:
            return None  
        
        engine = self.car.engine
        gearbox = self.car.gearbox
        vehicle = self.car.vehicle
        thermals = self.car.thermals
        wear = self.wear
        driver = self.driver

        raw = RawSimulationState(
            simulation_id=self.simulation_id,
            time=self.time,
            step=self.step_count,
            modules={
                "engine": vars(self.car.engine.state),
                "gearbox": vars(self.car.gearbox.state),
                "vehicle": vars(self.car.vehicle.state),
                "thermals": vars(self.car.thermals.state),
                "wear": vars(self.wear.state),
                "driver": vars(self.driver.state),
            }
        )

        self.update_modules(dt, engine, gearbox, vehicle, thermals, wear, driver)
        self.print_state()

        if engine.state.engine_rpm > 1.0 or vehicle.state.speed_kmh > 0.1:
            self.publish(dt, raw)

    def publish(self, dt: float, raw: RawSimulationState):
        """
        Updates the simulation timeline and broadcasts the captured state to all subscribers.
        """
        self.time += dt
        self.step_count += 1
        self.state_bus.publish(raw)

    def print_state(self):
        """
        Outputs the current vital telemetry to the console for real-time monitoring.
        """
        e = self.car.engine.state
        v = self.car.vehicle.state
        t = self.car.thermals.state
        g = self.car.gearbox.state
        w = self.wear.state
        d = self.driver.state

        print(
            f"RPM={e.engine_rpm:.0f} | "
            f"SPD={v.speed_kmh:.1f} | "
            f"TEMP={t.coolant_temp_c:.1f} | "
            f"OIL={t.oil_temp_c:.1f} | "
            f"FUEL={e.fuel_rate_lph:.1f} | "
            f"GEAR={g.current_gear} | "
            f"PEDAL={d.pedal:.2f} "
            f"THR={d.throttle:.2f} "
            f"RATE={d.throttle_rate:.2f} | "
            f"WEAR={w.engine_wear:.3f}"
        )