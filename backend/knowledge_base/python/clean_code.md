# Clean Code & Maintainability in Python

## Single Responsibility Principle (SRP)

Each function or class should have exactly one reason to change.

```python
# VIOLATION - function does too much
def process_order(order_data):
    # Validates input
    if not order_data.get("user_id"):
        raise ValueError("Missing user_id")
    # Saves to DB
    db.insert("orders", order_data)
    # Sends email
    send_email(order_data["email"], "Order confirmed")
    # Updates inventory
    for item in order_data["items"]:
        inventory.decrement(item["sku"], item["qty"])

# GOOD - separated concerns
def validate_order(order_data): ...
def save_order(order_data): ...
def notify_customer(order_data): ...
def update_inventory(order_data): ...

def process_order(order_data):
    validate_order(order_data)
    save_order(order_data)
    notify_customer(order_data)
    update_inventory(order_data)
```

## DRY — Don't Repeat Yourself

Duplicated code creates maintenance burden and inconsistency risk.

```python
# WET (Write Everything Twice)
def get_admin_users():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE role='admin'")
    return cur.fetchall()

def get_active_users():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE active=true")
    return cur.fetchall()

# DRY
def query_users(condition: str, params=()) -> list:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE {condition}", params)
    return cur.fetchall()
```

## Magic Numbers and Constants

```python
# BAD - magic numbers
if status_code == 404:
    ...
time.sleep(86400)

# GOOD - named constants
HTTP_NOT_FOUND = 404
SECONDS_PER_DAY = 86400

if status_code == HTTP_NOT_FOUND:
    ...
time.sleep(SECONDS_PER_DAY)
```

## Type Hints

Always use type hints for function signatures (Python 3.10+).

```python
# Without type hints - ambiguous
def calculate(data, threshold):
    ...

# With type hints - clear contract
def calculate(data: list[float], threshold: float = 0.5) -> dict[str, float]:
    ...
```

## Exception Handling

```python
# BAD - swallows all errors silently
try:
    result = risky_operation()
except:
    pass

# GOOD - specific exceptions, proper logging
import logging
logger = logging.getLogger(__name__)

try:
    result = risky_operation()
except ValueError as e:
    logger.warning("Invalid input: %s", e)
    raise
except ConnectionError as e:
    logger.error("Network failure: %s", e)
    raise RuntimeError("Service unavailable") from e
```

## Context Managers

Always use context managers for resource management.

```python
# BAD - resource leak if exception occurs
f = open("data.txt")
data = f.read()
f.close()

# GOOD
with open("data.txt") as f:
    data = f.read()
```

## Docstrings

```python
def calculate_discount(price: float, discount_pct: float) -> float:
    """
    Calculate discounted price.

    Args:
        price: Original price in USD. Must be non-negative.
        discount_pct: Discount percentage (0–100).

    Returns:
        Final price after discount.

    Raises:
        ValueError: If price is negative or discount_pct is out of range.
    """
    if price < 0:
        raise ValueError(f"Price must be non-negative, got {price}")
    if not 0 <= discount_pct <= 100:
        raise ValueError(f"Discount must be 0-100, got {discount_pct}")
    return price * (1 - discount_pct / 100)
```

## Naming Conventions (PEP 8)

- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`
- Avoid single-letter names except in short loops (`i`, `x`, `k`)

## Code Complexity Metrics

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Cyclomatic Complexity | ≤5 | 6–10 | >10 |
| Function length (lines) | ≤20 | 21–50 | >50 |
| Parameter count | ≤3 | 4–5 | >5 |
| Nesting depth | ≤3 | 4 | >4 |
