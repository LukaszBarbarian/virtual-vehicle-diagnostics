import time

from simulator.core.car_builder import CarBuilder
from simulator.core.car_profile import CarProfileLoader
from simulator.modules.driver import DriverInput
from simulator.modules.engine import EngineInput
from simulator.modules.gearbox import GearboxInput
from simulator.modules.thermals import ThermalInput
from simulator.modules.vehicle import VehicleInput
from simulator.modules.wear import WearInput, WearModule, WearState


dt = 0.1

# ============================
# Load car profile
# ============================

config = CarProfileLoader.load("config/cars/lambo.yaml")

engine, gearbox, vehicle, thermals, driver = CarBuilder.build(config)

# ============================
# Apply profile parameters to modules
# (TO JEST KLUCZOWA CZĘŚĆ)
# ============================

engine.state.rotational_inertia = config.engine.rotational_inertia
gearbox.engine_max_rpm = engine.max_rpm
engine.vehicle = vehicle


# ============================
# Other systems
# ============================


wear = WearModule(WearState(
    engine_wear=0.0,
    gearbox_wear=0.0,
    cooling_efficiency_loss=0.0,
    torque_loss_factor=0.0
))

# ============================
# Simulation loop
# ============================

while True:
    driver.input = DriverInput(
    engine_rpm=engine.state.engine_rpm,
    max_rpm=engine.max_rpm
    )
    
    driver.update(dt)

    # gearbox uses engine_rpm from previous step OR uses driver's throttle heuristics;
    # ale żeby mieć gear_ratio_total current, update gearbox BEFORE engine (można też keep two-step)
    gearbox.input = GearboxInput(
        engine_rpm=engine.state.engine_rpm,
        throttle=driver.output.throttle,
        vehicle_speed=vehicle.state.speed_kmh
    )
    gearbox.update(dt)

    # teraz przekaż totalne przełożenie do engine
    engine.input = EngineInput(
        throttle=driver.output.throttle,
        current_gear=gearbox.state.current_gear,
        vehicle_speed=vehicle.state.speed_kmh,
        ambient_temp_c=15.0,
        cooling_efficiency=1.0 - wear.state.cooling_efficiency_loss,
        torque_loss_factor=wear.state.torque_loss_factor,
        clutch_factor=0.0 if gearbox.state.shift_event else 1.0,
        gear_ratio_total=gearbox.output.gear_ratio,
        wheel_radius_m=vehicle.wheel_radius,
        vehicle_acc_mps2=vehicle.state.acc_mps2,
        vehicle_mass_kg=config.vehicle.mass_kg
    )
    engine.update(dt)

    # vehicle now:
    vehicle.input = VehicleInput(
        torque_nm=engine.output.torque_nm,
        gear_ratio=gearbox.output.gear_ratio,
        brake=driver.output.brake,
        cargo_mass_kg=driver.output.cargo_mass_kg,
        road_incline_pct=0.0
    )
    vehicle.update(dt)

    # Thermals
    thermals.input = ThermalInput(
        heat_kw=engine.output.heat_kw,
        vehicle_speed=vehicle.state.speed_kmh,
        ambient_temp_c=15.0,
        cooling_efficiency=1.0 - wear.state.cooling_efficiency_loss
    )
    thermals.update(dt)

    # Wear
    wear.input = WearInput(
        engine_temp_c=thermals.state.coolant_temp_c,
        oil_temp_c=thermals.state.oil_temp_c,
        load=vehicle.state.load,
        engine_rpm=engine.state.engine_rpm,
        gearbox_temp_c=gearbox.state.gearbox_temp_c
    )
    wear.update(dt)

    print(
        f"RPM={engine.state.engine_rpm:.2f} | "
        f"SPD={vehicle.state.speed_kmh:.1f} | "
        f"TEMP={thermals.state.coolant_temp_c:.1f} | "
        f"FUEL={engine.state.fuel_rate_lph:.1f} | "
        
        f"GEAR={gearbox.state.current_gear} | "
        f"WEAR={wear.state.engine_wear:.3f}"
    )

    time.sleep(dt + 0.2)
