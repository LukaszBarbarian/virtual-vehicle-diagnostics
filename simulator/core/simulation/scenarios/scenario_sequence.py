class ScenarioSequence:
    def __init__(self, scenarios):
        self.scenarios = scenarios
        self.current_idx = 0
        self.active = None

    def reset(self):
        self.current_idx = 0
        self.active = self.scenarios[0]
        self.active.reset()

    def step(self, t, state):
        if self.active is None:
            self.reset()

        cmd = self.active.get_driver_command(t, state)

        # 🔁 tu później możesz dodać warunek zakończenia scenariusza
        return cmd

    @property
    def name(self):
        return self.active.name if self.active else "none"
