class StateBus:
    """
    A simple event dispatcher that manages communication between the simulation core and external listeners.
    """
    def __init__(self):
        """
        Initializes an empty registry of event subscribers.
        """
        self.subscribers = []

    def subscribe(self, fn):
        """
        Registers a callback function to receive updates whenever a new simulation state is published.
        """
        self.subscribers.append(fn)

    def publish(self, raw_state):
        """
        Broadcasts the current simulation state to all registered subscribers sequentially.
        """
        for fn in self.subscribers:
            fn(raw_state)

    def clear_subscribers(self):
        """
        Resets the subscriber list to ensure a clean state and prevent potential memory leaks.
        """
        self.subscribers = []