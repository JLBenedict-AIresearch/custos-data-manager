# src.shared.messages

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Message:
    """The base class for all messages (Events and Commands) in the system."""
    pass

@dataclass(frozen=True)
class Command(Message):
    """An imperative request for the system to perform an action."""
    pass

@dataclass(frozen=True)
class DomainEvent(Message):
    """A past-tense fact that occurred in the domain."""
    event_id: str = field(
        default_factory=lambda: str(uuid.uuid4()), 
        init=False
    )
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

