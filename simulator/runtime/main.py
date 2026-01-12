from simulator.runtime import SimulationRuntime


def main():
    runtime = SimulationRuntime().bootstrap()
    runtime.start_engine(0.1)

if __name__ == "__main__":
    main()
