# Python Performance Optimization Patterns

## List Comprehensions vs Loops

List comprehensions are typically 30–50% faster than equivalent for-loops in CPython.

```python
# Slow
result = []
for i in range(1000):
    if i % 2 == 0:
        result.append(i * 2)

# Fast
result = [i * 2 for i in range(1000) if i % 2 == 0]
```

## Generator Expressions for Memory Efficiency

Use generators when you don't need all results at once.

```python
# Memory-heavy: loads entire list into RAM
total = sum([x**2 for x in range(10_000_000)])

# Memory-efficient: streams values
total = sum(x**2 for x in range(10_000_000))
```

## String Concatenation

String concatenation in a loop is O(n²) due to immutability.

```python
# SLOW - O(n²)
result = ""
for word in words:
    result += word + " "

# FAST - O(n)
result = " ".join(words)
```

## Dictionary Lookups vs Linear Search

```python
# O(n) linear scan
def find_user_slow(users_list, user_id):
    for user in users_list:
        if user["id"] == user_id:
            return user

# O(1) hash lookup
def find_user_fast(users_dict, user_id):
    return users_dict.get(user_id)
```

## Caching with functools.lru_cache

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

## NumPy Vectorization

Avoid Python loops over numerical arrays; use NumPy vectorized operations.

```python
import numpy as np

# SLOW - Python loop
result = [x * 2 + 1 for x in data]

# FAST - NumPy vectorized (100x+ faster for large arrays)
data = np.array(data)
result = data * 2 + 1
```

## Profiling Tools

- `cProfile`: built-in function-level profiler
- `line_profiler`: line-by-line profiling
- `memory_profiler`: track memory usage
- `py-spy`: sampling profiler, low overhead

```python
import cProfile
cProfile.run('my_function()')
```

## Database Query Optimization

N+1 query problem — a common ORM pitfall:

```python
# BAD - N+1 queries
for user in session.query(User).all():
    print(user.orders)  # triggers a new query per user

# GOOD - eager loading
from sqlalchemy.orm import joinedload
users = session.query(User).options(joinedload(User.orders)).all()
```

## Cyclomatic Complexity

High cyclomatic complexity (>10) makes code harder to test and maintain.
Refactor deeply nested conditionals into smaller functions.

```python
# High complexity (CC=6)
def process(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y
        else:
            return x
    else:
        return 0

# Lower complexity (CC=2 per function)
def process(x, y, z):
    if x <= 0:
        return 0
    return x + _sum_positives(y, z)

def _sum_positives(y, z):
    return y + (z if z > 0 else 0) if y > 0 else 0
```
