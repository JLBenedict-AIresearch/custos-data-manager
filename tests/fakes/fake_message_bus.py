# tests.conftests.fake_message_bus


from src.shared.messages import Message

class FakeMessageBus:
    def __init__(self):
        self.published_messages: list[Message] = []

    def handle(self, message: Message) -> None:
        """Mocks the routing of messages by just storing them."""
        self.published_messages.append(message)
        
    def clear(self) -> None:
        """Clears the bus between tests."""
        self.published_messages.clear()