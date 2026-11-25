# Python Performance Guide (Near-Duplicate for Dedup Testing)

## List Comprehensions vs For Loops

List comprehensions are generally 30–50% faster than equivalent for-loops in CPython due to bytecode optimization.

```python
# Slower approach
result = []
for i in range(1000):
    if i % 2 == 0:
        result.append(i * 2)

# Faster approach
result = [i * 2 for i in range(1000) if i % 2 == 0]
```

## Generator Expressions for Memory Efficiency

When processing large datasets, generators avoid loading everything into memory.

```python
# Memory-heavy
total = sum([x**2 for x in range(10_000_000)])

# Memory-efficient generator
total = sum(x**2 for x in range(10_000_000))
```

## String Concatenation in Loops

String concatenation in loops creates O(n²) allocations because strings are immutable.

```python
# Inefficient - O(n²)
result = ""
for word in words:
    result += word + " "

# Efficient - O(n)
result = " ".join(words)
```

## functools.lru_cache

Memoization eliminates redundant computation for pure functions.

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
```

NOTE: This document is intentionally very similar to performance_patterns.md to test deduplication in the retrieval pipeline.
