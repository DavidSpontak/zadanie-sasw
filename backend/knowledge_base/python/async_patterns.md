# Async Python Best Practices

## When to Use async/await

Use async when:
- Making I/O-bound calls (HTTP, database, file system)
- Building servers handling concurrent connections
- Writing scrapers or parallel API callers

Do NOT use async for CPU-bound work — use `multiprocessing` or `concurrent.futures.ProcessPoolExecutor` instead.

## Basic async/await

```python
import asyncio
import httpx

async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

async def main():
    result = await fetch_url("https://api.example.com/data")
    print(result)

asyncio.run(main())
```

## Concurrent Requests with asyncio.gather

```python
async def fetch_all(urls: list[str]) -> list[str]:
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        return [r.text for r in responses if not isinstance(r, Exception)]
```

## asyncio.gather vs asyncio.TaskGroup (Python 3.11+)

```python
# asyncio.gather — returns results, handles exceptions with return_exceptions
results = await asyncio.gather(task1(), task2(), return_exceptions=True)

# TaskGroup — cancels all on first failure (stricter)
async with asyncio.TaskGroup() as tg:
    t1 = tg.create_task(task1())
    t2 = tg.create_task(task2())
# Both tasks complete before continuing
```

## Common Pitfalls

### Blocking calls inside async functions

```python
# BAD - blocks the event loop
async def bad_handler():
    time.sleep(5)  # blocks entire event loop!
    data = open("big_file.txt").read()  # synchronous I/O

# GOOD - use async equivalents or thread executor
import asyncio
import aiofiles

async def good_handler():
    await asyncio.sleep(5)
    async with aiofiles.open("big_file.txt") as f:
        data = await f.read()
```

### Forgetting to await

```python
# BUG - coroutine is created but never awaited
async def process():
    fetch_data()  # returns coroutine, never executed!

# FIX
async def process():
    await fetch_data()
```

## Async Context Managers and Iterators

```python
class AsyncDatabaseSession:
    async def __aenter__(self):
        self.conn = await create_connection()
        return self.conn

    async def __aexit__(self, *args):
        await self.conn.close()

async def main():
    async with AsyncDatabaseSession() as db:
        result = await db.execute("SELECT 1")
```

## Semaphore for Rate Limiting

```python
async def fetch_with_limit(urls: list[str], max_concurrent: int = 10):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_fetch(url):
        async with semaphore:
            async with httpx.AsyncClient() as client:
                return await client.get(url)

    return await asyncio.gather(*[bounded_fetch(u) for u in urls])
```

## Timeout Handling

```python
async def fetch_with_timeout(url: str, timeout_seconds: float = 5.0):
    try:
        async with asyncio.timeout(timeout_seconds):
            async with httpx.AsyncClient() as client:
                return await client.get(url)
    except asyncio.TimeoutError:
        raise RuntimeError(f"Request to {url} timed out after {timeout_seconds}s")
```
