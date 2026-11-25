# Python Testing Best Practices

## Unit Test Structure — AAA Pattern

Every test should follow Arrange → Act → Assert.

```python
import pytest
from myapp.calculator import divide

def test_divide_positive_numbers():
    # Arrange
    numerator = 10
    denominator = 2

    # Act
    result = divide(numerator, denominator)

    # Assert
    assert result == 5.0

def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)
```

## Test Coverage Goals

- Aim for ≥80% line coverage as a minimum baseline.
- 100% coverage does not mean correct tests — focus on meaningful assertions.
- Use `pytest-cov` to measure: `pytest --cov=myapp --cov-report=term-missing`

## Fixtures and Dependency Injection

```python
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value = [{"id": 1, "name": "Alice"}]
    return db

def test_get_users(mock_db):
    from myapp.users import get_users
    users = get_users(db=mock_db)
    assert len(users) == 1
    mock_db.query.assert_called_once_with("SELECT * FROM users")
```

## Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
    ("123", "123"),
])
def test_to_upper(input, expected):
    assert input.upper() == expected
```

## Mocking External Services

```python
from unittest.mock import patch

def test_fetch_weather():
    mock_response = {"temp": 22, "condition": "sunny"}
    with patch("myapp.weather.requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.status_code = 200

        result = fetch_weather("London")
        assert result["temp"] == 22
```

## Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(st.integers(), st.integers().filter(lambda x: x != 0))
def test_divide_properties(a, b):
    result = divide(a, b)
    # Property: result * b should equal a (within float precision)
    assert abs(result * b - a) < 1e-9
```

## Integration Test Patterns

Separate unit and integration tests:

```
tests/
  unit/          # fast, no I/O, mocked dependencies
  integration/   # real DB, real HTTP (marked @pytest.mark.integration)
  e2e/           # full system tests
```

```python
@pytest.mark.integration
def test_user_creation_e2e(test_db):
    user = create_user(db=test_db, name="Bob", email="bob@example.com")
    assert user.id is not None
    assert test_db.query(User).filter_by(email="bob@example.com").first() is not None
```

## Anti-Patterns to Avoid

1. **Testing implementation details** instead of behavior
2. **Brittle assertions** on exact string messages
3. **Global state** that leaks between tests — always use fixtures
4. **Not testing edge cases**: empty inputs, None values, boundary values
5. **Sleeping in tests** — use mocks for time-dependent code

## Test Naming Convention

`test_<function_name>_<scenario>_<expected_result>`

```python
def test_divide_by_zero_raises_zero_division_error(): ...
def test_create_user_with_duplicate_email_raises_value_error(): ...
def test_get_active_users_returns_only_active_records(): ...
```
