class StateBus:
    def __init__(self):
        self.subscribers = []

    def subscribe(self, fn):
        self.subscribers.append(fn)

    def publish(self, raw_state):
        for fn in self.subscribers:
            fn(raw_state)
