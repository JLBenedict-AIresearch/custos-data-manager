# src.shared.runner_interface.py

import abc

from src.shared.interfaces.message_bus_interface import AbstractMessageBus


class AbstractBackgroundRunner(abc.ABC):
    """
    Interface for any service that listens for external events 
    and triggers the data pipeline. Maybe require inheritance overrides for special methods in adapters.
    """
    def __init__(self, incoming_directory: str, message_bus: AbstractMessageBus):
        self.incoming_directory = incoming_directory
        self.bus = message_bus

    @abc.abstractmethod
    def start(self):
        """Starts the background listening process."""
        raise NotImplementedError

    @abc.abstractmethod
    def stop(self):
        """Gracefully shuts down the listener."""
        raise NotImplementedError