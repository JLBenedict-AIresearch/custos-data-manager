# src.shared.message_bus

import functools
from typing import Any, Callable, Sequence, Type, Union

import structlog

from src.infrastructure.logging import log_domain_error
from src.pipeline.events import DomainEvent, FileProcessingAborted, SystemFaultEvent
from src.shared.errors import MissingCommandHandlerError, UnknownMessageTypeError, CustosSystemError
from src.shared.interfaces.message_bus_interface import AbstractMessageBus
from src.shared.messages import Command, DomainEvent, Message

logger = structlog.get_logger(__name__)

class MessageBus(AbstractMessageBus):
    def __init__(self):

        self.event_handlers: dict[Type[DomainEvent], list[Callable]] = {}

        self.command_handlers: dict[Type[Command], Callable] = {}

    def subscribe_event(self, event_type: Type[DomainEvent], handler: Callable):
        """Registers a handler to listen for a specific event."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def register_command(self, command_type: Type[Command], handler: Callable):
        """Registers a single executor for a command."""
        self.command_handlers[command_type] = handler

    def handle(self, initial_message: Message) -> None:
        commands: list[Command] = []
        events: list[DomainEvent] = []
        
        if initial_message: 
            if isinstance(initial_message, DomainEvent):
                events.append(initial_message)
            elif isinstance(initial_message, Command):
                commands.append(initial_message)
            else: 
                raise UnknownMessageTypeError(type(initial_message))
            
        while commands or events:
            
            while events:
                event = events.pop(0)
                new_messages = self._handle_event(event)
                
                if isinstance(event, SystemFaultEvent):
                    commands = [c for c in commands if getattr(c, 'file_id', None) != event.file_id]
                    events = [e for e in events if getattr(e, 'file_id', None) != event.file_id]
                
                self._enqueue_messages(new_messages, commands, events)
                
            if commands:
                command = commands.pop(0)
                new_messages = self._handle_command(command)
                self._enqueue_messages(new_messages, commands, events)

    def _enqueue_messages(self, messages: Sequence[Message], commands: list, events: list) -> None:
        """Helper to sort returned messages into the correct queues."""
        for msg in messages:
            if isinstance(msg, DomainEvent):
                events.append(msg)
            elif isinstance(msg, Command):
                commands.append(msg)
            else:
                raise UnknownMessageTypeError(type(msg))

    def _handle_event(self, event: DomainEvent) -> Sequence[Message]:
        handlers = self.event_handlers.get(type(event), [])
        
        results: list[Message] = []
        for handler in handlers: 
            try: 
                results.extend(handler(event) or [])
        
            except Exception as e:
                if isinstance(handler, functools.partial):
                    handler_name = handler.func.__name__
                else:
                    handler_name = getattr(handler, "__name__", str(handler))
                    
                log_domain_error(e, event_type=type(event).__name__, handler_name=handler_name)

        return results 

    def _handle_command(self, command: Command) -> Sequence[Message]:
        handler = self.command_handlers.get(type(command))
        if not handler:
            raise MissingCommandHandlerError(type(command))
        
        try: 
            return handler(command) or []

        except CustosSystemError as e:
            log_domain_error(e, command_type=type(command).__name__)
            return [SystemFaultEvent(
                file_id=getattr(command, 'file_id', None),
                filename=getattr(command, 'filename', 'UNKNOWN'),
                filepath=getattr(command, 'filepath', 'unknown'),
                error_type=type(e).__name__,
                message=str(e),
            )]
        
    def publish(self, message: Message) -> None: 
        """Set-up for future addition of a message broker, if desired"""
        pass