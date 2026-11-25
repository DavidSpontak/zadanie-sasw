# C# Performance Optimization Patterns

## String Concatenation in Loops

Strings are immutable, so `+=` in a loop allocates a new string every iteration (O(n²) copying).

```csharp
// SLOW - O(n²)
var result = "";
foreach (var word in words)
    result += word + " ";

// FAST - O(n)
var sb = new StringBuilder();
foreach (var word in words)
    sb.Append(word).Append(' ');
var result2 = sb.ToString();

// SIMPLEST
var result3 = string.Join(" ", words);
```

## LINQ: Any() vs Count()

`Count()` on an `IEnumerable<T>` may enumerate the entire sequence just to compare with zero.
`Any()` stops at the first element. On collections, use the `Count` / `Length` property.

```csharp
// SLOW
if (orders.Count() > 0) { ... }

// FAST
if (orders.Any()) { ... }
if (list.Count > 0) { ... }   // List<T>, arrays: property, O(1)
```

## Multiple Enumeration of IEnumerable

A LINQ query is re-executed every time it is enumerated. If it hits a database or does heavy work,
materialize it once with `ToList()` or `ToArray()`.

```csharp
// SLOW - the query runs twice
IEnumerable<Order> pending = orders.Where(o => o.Status == Status.Pending);
var count = pending.Count();
var total = pending.Sum(o => o.Amount);

// FAST - runs once
var pendingList = orders.Where(o => o.Status == Status.Pending).ToList();
```

## Dictionary Lookups vs Linear Search

```csharp
// O(n) linear scan
var user = users.FirstOrDefault(u => u.Id == userId);

// O(1) hash lookup
var usersById = users.ToDictionary(u => u.Id);
if (usersById.TryGetValue(userId, out var found)) { ... }

// Avoid double lookups: ContainsKey + indexer does two lookups, TryGetValue does one
```

## EF Core: N+1 Queries and Eager Loading

Accessing a navigation property inside a loop can trigger one query per row (N+1 problem).

```csharp
// BAD - N+1 queries (with lazy loading enabled)
foreach (var customer in db.Customers.ToList())
    Console.WriteLine(customer.Orders.Count);

// GOOD - eager loading with Include
var customers = await db.Customers.Include(c => c.Orders).ToListAsync();

// BETTER for read-only views - project only what you need
var summaries = await db.Customers
    .Select(c => new { c.Name, OrderCount = c.Orders.Count })
    .ToListAsync();
```

## EF Core: AsNoTracking for Read-Only Queries

The change tracker costs memory and CPU. For queries whose results you won't update, use `AsNoTracking()`.

```csharp
var products = await db.Products
    .AsNoTracking()
    .Where(p => p.IsActive)
    .ToListAsync(ct);
```

## Reusing HttpClient

Creating a new `HttpClient` per request can exhaust sockets under load. Use `IHttpClientFactory`
(or one long-lived instance with `PooledConnectionLifetime` set so DNS changes are picked up).

```csharp
// BAD
using var client = new HttpClient();
var json = await client.GetStringAsync(url);

// GOOD - register once, inject everywhere
builder.Services.AddHttpClient<WeatherClient>(c => c.BaseAddress = new Uri("https://api.example.com"));

public class WeatherClient(HttpClient http)
{
    public Task<string> GetAsync(string city) => http.GetStringAsync($"/weather/{city}");
}
```

## Caching with IMemoryCache

```csharp
builder.Services.AddMemoryCache();

public async Task<Product?> GetProductAsync(int id) =>
    await _cache.GetOrCreateAsync($"product:{id}", entry =>
    {
        entry.AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(5);
        return _db.Products.FindAsync(id).AsTask();
    });
```

## Avoiding Allocations: Span<T> and ArrayPool

`Span<T>` slices memory without copying, and `ArrayPool<T>` reuses buffers instead of allocating.

```csharp
// Allocates a new string
var year = date.Substring(0, 4);

// No allocation
ReadOnlySpan<char> yearSpan = date.AsSpan(0, 4);
int parsed = int.Parse(yearSpan);

byte[] buffer = ArrayPool<byte>.Shared.Rent(4096);
try { /* use buffer */ }
finally { ArrayPool<byte>.Shared.Return(buffer); }
```

## Case-Insensitive String Comparison

`ToLower()` / `ToUpper()` allocate new strings and are culture-sensitive.

```csharp
// SLOW and culture-dependent
if (a.ToLower() == b.ToLower()) { ... }

// FAST and correct for identifiers, keys, file names
if (string.Equals(a, b, StringComparison.OrdinalIgnoreCase)) { ... }
```

## Profiling and Benchmarking Tools

- `BenchmarkDotNet`: micro-benchmarks with statistics (always run in Release mode)
- `dotnet-counters`: live CPU, GC and thread pool metrics
- `dotnet-trace`: CPU sampling traces
- Visual Studio / Rider profilers for allocations and hot paths

```csharp
[MemoryDiagnoser]
public class JoinBenchmarks
{
    private readonly string[] _words = Enumerable.Repeat("word", 1000).ToArray();

    [Benchmark] public string Join() => string.Join(" ", _words);
}
```

## Cyclomatic Complexity

High cyclomatic complexity (>10) makes code harder to test and maintain.
Replace nested conditionals with guard clauses and smaller methods.

```csharp
// High complexity
decimal Process(int x, int y, int z)
{
    if (x > 0)
    {
        if (y > 0)
        {
            if (z > 0) return x + y + z;
            else return x + y;
        }
        else return x;
    }
    else return 0;
}

// Lower complexity - guard clauses
decimal Process(int x, int y, int z)
{
    if (x <= 0) return 0;
    if (y <= 0) return x;
    return x + y + Math.Max(z, 0);
}
```
