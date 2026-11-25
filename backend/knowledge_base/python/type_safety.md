# Python Type Safety and Dataclasses

## dataclasses vs TypedDict vs Pydantic

### dataclass — for internal data structures
```python
from dataclasses import dataclass, field

@dataclass
class Order:
    order_id: str
    user_id: str
    items: list[str] = field(default_factory=list)
    total: float = 0.0
    
    def add_item(self, item: str, price: float) -> None:
        self.items.append(item)
        self.total += price
```

### TypedDict — for dictionary shapes (JSON, kwargs)
```python
from typing import TypedDict

class UserPayload(TypedDict):
    name: str
    email: str
    age: int

def create_user(payload: UserPayload) -> None:
    ...
```

### Pydantic — for validation + serialization (APIs, configs)
```python
from pydantic import BaseModel, EmailStr, field_validator

class UserRequest(BaseModel):
    name: str
    email: EmailStr
    age: int

    @field_validator("age")
    @classmethod
    def age_must_be_positive(cls, v):
        if v < 0:
            raise ValueError("age must be non-negative")
        return v
```

## TypeVar and Generic Functions

```python
from typing import TypeVar

T = TypeVar("T")

def first(items: list[T]) -> T | None:
    return items[0] if items else None

# Type checker knows: first([1, 2, 3]) returns int | None
# Type checker knows: first(["a", "b"]) returns str | None
```

## Protocol for Structural Typing

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Drawable(Protocol):
    def draw(self) -> None: ...
    def resize(self, factor: float) -> None: ...

def render(shape: Drawable) -> None:
    shape.draw()

# Any object with draw() and resize() satisfies Drawable
# No need to inherit from it
```

## Literal Types

```python
from typing import Literal

Direction = Literal["north", "south", "east", "west"]

def move(direction: Direction, steps: int) -> None:
    ...

move("north", 5)   # OK
move("up", 5)      # Type error caught by mypy
```

## Final and ClassVar

```python
from typing import Final, ClassVar

MAX_RETRIES: Final = 3   # Cannot be reassigned

class Config:
    DEFAULT_TIMEOUT: ClassVar[float] = 30.0   # Class-level constant
    
    def __init__(self, timeout: float = Config.DEFAULT_TIMEOUT):
        self.timeout = timeout
```

## Overload for Multiple Signatures

```python
from typing import overload

@overload
def process(data: str) -> str: ...
@overload
def process(data: bytes) -> bytes: ...
@overload
def process(data: list[int]) -> list[int]: ...

def process(data):
    if isinstance(data, str):
        return data.upper()
    elif isinstance(data, bytes):
        return data.upper()
    else:
        return [x * 2 for x in data]
```

## mypy Configuration

```ini
# mypy.ini
[mypy]
python_version = 3.12
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```
