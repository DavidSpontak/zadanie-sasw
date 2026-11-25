# Python Design Patterns

## Factory Pattern

```python
from abc import ABC, abstractmethod

class Notification(ABC):
    @abstractmethod
    def send(self, message: str) -> None: ...

class EmailNotification(Notification):
    def send(self, message: str) -> None:
        print(f"Email: {message}")

class SMSNotification(Notification):
    def send(self, message: str) -> None:
        print(f"SMS: {message}")

def notification_factory(channel: str) -> Notification:
    match channel:
        case "email": return EmailNotification()
        case "sms":   return SMSNotification()
        case _: raise ValueError(f"Unknown channel: {channel}")
```

## Singleton Pattern

```python
class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connected = False
        return cls._instance

    def connect(self, url: str) -> None:
        if not self._connected:
            # establish connection
            self._connected = True
```

## Observer Pattern

```python
from typing import Callable

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable) -> None:
        self._handlers.setdefault(event, []).append(handler)

    def publish(self, event: str, data=None) -> None:
        for handler in self._handlers.get(event, []):
            handler(data)
```

## Strategy Pattern

```python
from typing import Protocol

class SortStrategy(Protocol):
    def sort(self, data: list) -> list: ...

class QuickSort:
    def sort(self, data: list) -> list:
        if len(data) <= 1:
            return data
        pivot = data[len(data) // 2]
        left = [x for x in data if x < pivot]
        mid  = [x for x in data if x == pivot]
        right = [x for x in data if x > pivot]
        return self.sort(left) + mid + self.sort(right)

class DataProcessor:
    def __init__(self, strategy: SortStrategy):
        self._strategy = strategy

    def process(self, data: list) -> list:
        return self._strategy.sort(data)
```

## Dependency Injection

```python
class UserService:
    def __init__(self, db, mailer, logger):
        # Inject all dependencies — no hidden globals
        self.db = db
        self.mailer = mailer
        self.logger = logger

    def create_user(self, name: str, email: str):
        user = self.db.insert({"name": name, "email": email})
        self.mailer.send_welcome(email)
        self.logger.info(f"Created user {user.id}")
        return user
```

## Context Object Pattern (avoiding long parameter lists)

```python
from dataclasses import dataclass

@dataclass
class RequestContext:
    user_id: str
    tenant_id: str
    locale: str
    trace_id: str

def process_payment(ctx: RequestContext, amount: float) -> None:
    # All context travels together
    log_audit(ctx.trace_id, ctx.user_id, amount)
```
