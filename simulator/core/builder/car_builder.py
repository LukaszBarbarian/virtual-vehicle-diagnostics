from simulator.modules.car import Car
from simulator.modules.engine import EngineModule, EngineState
from simulator.modules.gearbox import GearboxModule, GearboxState
from simulator.modules.vehicle import VehicleModule, VehicleState
from simulator.modules.thermals import ThermalModule, ThermalState
from simulator.core.models.model_specification import CarSpecification

class CarBuilder:
    """
    Factory class responsible for assembling a complete Car object from a technical specification.
    """
    @staticmethod
    def build(car_spec: CarSpecification) -> Car:
        """
        Instantiates and configures all individual vehicle modules to create a functional car simulation.
        """
        engine = EngineModule(
            EngineState(
                engine_rpm=0.0,
                engine_temp_c=20.0,
                oil_temp_c=20.0,
                efficiency=car_spec.engine.efficiency,
                rotational_inertia=car_spec.engine.rotational_inertia
            )
        )
        engine.apply_config(car_spec.engine)

        gearbox = GearboxModule(
            GearboxState(
                current_gear=1,
                gear_ratio=0.0,
                gearbox_temp_c=30.0,
                shift_event=False
            )
        )
        gearbox.apply_config(car_spec.gearbox)

        vehicle = VehicleModule(
            VehicleState(
                speed_kmh=0.0,
                acc_mps2=0.0,
                mass_kg=car_spec.vehicle.mass_kg,
                load=0.0
            )
        )
        vehicle.apply_config(car_spec.vehicle)

        thermals = ThermalModule(
            ThermalState(
                coolant_temp_c=20.0,
                oil_temp_c=20.0,
                fan_active=False,
                thermal_mass=car_spec.thermal.thermal_mass
            )
        )
        thermals.apply_config(car_spec.thermal)

        return Car(engine, gearbox, thermals, vehicle)