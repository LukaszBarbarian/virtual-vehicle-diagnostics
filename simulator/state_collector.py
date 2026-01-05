import time


class StateCollector:
    def collect(self, **modules):
        snapshot = {}

        for name, module in modules.items():
            snapshot[name] = module.state.__dict__.copy()

        snapshot["timestamp"] = time.time()
        return snapshot
