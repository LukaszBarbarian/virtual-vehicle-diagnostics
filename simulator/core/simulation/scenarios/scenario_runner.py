from simulator.core.simulation.scenarios.driver_scenario import DrivingScenario
from simulator.core.simulation.scenarios.scenario_sequence import ScenarioSequence
from simulator.runtime.runtime import SimulationRuntime
from streaming.kafka.producers.driver_command import DriverCommandPublisher


class ScenarioRunner:
    def __init__(
        self,
        scenario_sequence: ScenarioSequence,
        simulation_runtime: SimulationRuntime,
        driver_publisher: DriverCommandPublisher
    ):
        self.scenario_sequence = scenario_sequence
        self.simulation = simulation_runtime
        self.publisher = driver_publisher

    def step(self, dt: float):
        t = self.simulation.sim.time
        state = self.simulation.sim

        cmd = self.scenario_sequence.step(t, state)

        if not cmd:
            return

        pedal = cmd.get("pedal")
        if pedal is None:
            return

        # 🔑 safety clamp
        pedal = max(0.0, min(1.0, pedal))

        self.publisher.set_throttle(pedal)
