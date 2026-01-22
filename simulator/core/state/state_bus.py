class StateBus:
    def __init__(self):
        self.subscribers = []

    def subscribe(self, fn):
        """Adds a new listener to the state updates."""
        self.subscribers.append(fn)

    def publish(self, raw_state):
        """Sends the current simulation state to all active listeners."""
        for fn in self.subscribers:
            fn(raw_state)

    def clear_subscribers(self):
        """Removes all listeners to prevent memory leaks during session resets."""
        self.subscribers = []