# Error Handling and Logging in Python

## Structured Logging

Use structured logging (JSON format) for production systems.

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        })

logger = logging.getLogger("myapp")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

## Exception Hierarchy

Define custom exception hierarchies for your domain.

```python
class AppError(Exception):
    """Base exception for all application errors."""

class ValidationError(AppError):
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Validation failed for '{field}': {message}")

class NotFoundError(AppError):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} with id={id} not found")

class AuthorizationError(AppError):
    pass
```

## Retry with Exponential Backoff

```python
import time
import random
from functools import wraps

def retry(max_attempts=3, base_delay=1.0, exceptions=(Exception,)):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(delay)
        return wrapper
    return decorator

@retry(max_attempts=3, base_delay=0.5, exceptions=(ConnectionError, TimeoutError))
def call_external_api(url: str) -> dict:
    ...
```

## Circuit Breaker Pattern

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject calls
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = CircuitState.HALF_OPEN
            else:
                raise RuntimeError("Circuit breaker is OPEN")
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

## Logging Best Practices

```python
# BAD - using print
print("User created:", user_id)
print("ERROR: DB connection failed")

# GOOD - structured logging levels
logger.info("User created", extra={"user_id": user_id})
logger.error("DB connection failed", exc_info=True, extra={"retry": attempt})

# BAD - string formatting before check
logger.debug("Processing %s items: %s" % (len(items), expensive_serialize(items)))

# GOOD - lazy formatting (skipped if level not active)
logger.debug("Processing %d items: %r", len(items), items)
```

## Sentinel Values vs None

```python
# BAD - None can mean "not set" OR "explicitly null"
def get_config(key: str) -> str | None:
    return config.get(key)  # Is None "missing" or "set to null"?

# GOOD - sentinel distinguishes
_MISSING = object()

def get_config(key: str, default=_MISSING) -> str:
    value = config.get(key, _MISSING)
    if value is _MISSING:
        if default is _MISSING:
            raise KeyError(f"Config key '{key}' not found")
        return default
    return value
```
