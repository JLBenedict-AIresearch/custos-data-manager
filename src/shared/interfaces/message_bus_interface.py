# src.shared.message_bus_interface

from abc import ABC, abstractmethod
from typing import Callable, Type

from src.shared.messages import Command, DomainEvent, Message


class AbstractMessageBus(ABC):
    
    @abstractmethod
    def subscribe_event(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        pass

    @abstractmethod
    def register_command(self, command_type: Type[Command], handler: Callable) -> None:
        pass

    @abstractmethod
    def handle(self, initial_message: Message) -> None:
        pass
        
    @abstractmethod
    def publish(self, message: Message) -> None:
        pass
