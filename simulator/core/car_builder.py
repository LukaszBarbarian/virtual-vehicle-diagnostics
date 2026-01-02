from modules.driver import DriverModule, DriverState
from modules.engine import EngineModule, EngineState
from modules.gearbox import GearboxModule, GearboxState
from modules.vehicle import VehicleModule, VehicleState
from modules.thermals import ThermalModule, ThermalState


class CarBuilder:
    @staticmethod
    def build(config):

        # ================= ENGINE =================
        engine = EngineModule(
            EngineState(
                engine_rpm=0.0,
                engine_temp_c=20.0,
                oil_temp_c=20.0,
                efficiency=config.engine.efficiency,
                rotational_inertia=config.engine.rotational_inertia
            )
        )
        engine.apply_config(config.engine)

        # ================= GEARBOX =================
        gearbox = GearboxModule(
            GearboxState(
                current_gear=1,
                gear_ratio=0.0,
                gearbox_temp_c=30.0,
                shift_event=False
            )
        )
        gearbox.apply_config(config.gearbox)

        # ================= VEHICLE =================
        vehicle = VehicleModule(
            VehicleState(
                speed_kmh=0.0,
                acc_mps2=0.0,
                mass_kg=config.vehicle.mass_kg,
                load=0.0
            )
        )
        vehicle.apply_config(config.vehicle)

        # ================= THERMALS =================
        thermals = ThermalModule(
            ThermalState(
                coolant_temp_c=20.0,
                oil_temp_c=20.0,
                fan_active=False,
                thermal_mass=config.thermal.thermal_mass
            )
        )
        thermals.apply_config(config.thermal)

        # ================= DRIVER =================
        driver = DriverModule()
        driver.apply_config(config.driver)

        return engine, gearbox, vehicle, thermals, driver
