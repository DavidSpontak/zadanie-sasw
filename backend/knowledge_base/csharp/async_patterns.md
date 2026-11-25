# Async C# Best Practices

## When to Use async/await

Use async for I/O-bound work: HTTP calls, database queries, file and network access.
It frees the thread while waiting. Do NOT wrap CPU-bound work in `Task.Run` inside ASP.NET Core
request handlers; it only moves the work to another thread-pool thread.

```csharp
public async Task<string> FetchAsync(string url, CancellationToken ct)
{
    using var response = await _http.GetAsync(url, ct);
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadAsStringAsync(ct);
}
```

## Async All the Way: Avoid .Result and .Wait()

Blocking on a task with `.Result`, `.Wait()` or `.GetAwaiter().GetResult()` can deadlock in apps with a
synchronization context (WPF, WinForms, classic ASP.NET) and causes thread-pool starvation in ASP.NET Core.

```csharp
// BAD - sync over async
public User GetUser(int id) => _repo.GetUserAsync(id).Result;

// GOOD - make the caller async too
public async Task<User> GetUserAsync(int id) => await _repo.GetUserAsync(id);
```

## Avoid async void

`async void` methods can't be awaited, their exceptions can't be caught by the caller, and an unhandled
exception crashes the process. Only use `async void` for event handlers.

```csharp
// BAD
public async void SaveData() => await _repo.SaveAsync();

// GOOD
public async Task SaveDataAsync() => await _repo.SaveAsync();

// OK - event handler
private async void SaveButton_Click(object sender, EventArgs e) => await SaveDataAsync();
```

## Concurrent Requests with Task.WhenAll

Awaiting in a loop runs operations one after another. Start them all, then await together.

```csharp
// SLOW - sequential
var results = new List<string>();
foreach (var url in urls)
    results.Add(await _http.GetStringAsync(url));

// FAST - concurrent
var tasks = urls.Select(url => _http.GetStringAsync(url));
string[] results2 = await Task.WhenAll(tasks);
```

## Limiting Concurrency

Unbounded `Task.WhenAll` over thousands of items can overload a server. Limit the degree of parallelism.

```csharp
// .NET 6+
await Parallel.ForEachAsync(urls, new ParallelOptions { MaxDegreeOfParallelism = 10 },
    async (url, ct) => await ProcessAsync(url, ct));

// Or with SemaphoreSlim
var gate = new SemaphoreSlim(10);
var tasks = urls.Select(async url =>
{
    await gate.WaitAsync();
    try { return await _http.GetStringAsync(url); }
    finally { gate.Release(); }
});
```

## Cancellation Tokens

Accept a `CancellationToken` in async methods and pass it to every async call, so work stops when the
client disconnects or a timeout fires. ASP.NET Core binds `CancellationToken` parameters to the request.

```csharp
app.MapGet("/reports/{id}", async (int id, IReportService reports, CancellationToken ct) =>
    await reports.BuildAsync(id, ct));

public async Task<Report> BuildAsync(int id, CancellationToken ct)
{
    var data = await _db.Sales.Where(s => s.ReportId == id).ToListAsync(ct);
    ct.ThrowIfCancellationRequested();
    return Summarize(data);
}
```

## Timeouts

```csharp
// Timeout for a whole operation
using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
var data = await _http.GetStringAsync(url, cts.Token);

// .NET 6+: add a timeout to any task
var result = await SlowOperationAsync().WaitAsync(TimeSpan.FromSeconds(5));
```

## Task.Delay vs Thread.Sleep

`Thread.Sleep` blocks the thread. In async code use `await Task.Delay`, which releases it.

```csharp
// BAD - blocks a thread-pool thread
Thread.Sleep(1000);

// GOOD
await Task.Delay(1000, ct);
```

## ConfigureAwait(false) in Libraries

In reusable library code, `ConfigureAwait(false)` avoids resuming on the caller's synchronization context.
ASP.NET Core apps have no synchronization context, so application code there doesn't need it.

```csharp
public async Task<byte[]> ReadAllAsync(Stream stream)
{
    using var ms = new MemoryStream();
    await stream.CopyToAsync(ms).ConfigureAwait(false);
    return ms.ToArray();
}
```

## Forgetting to Await

A task that is never awaited runs unobserved: its exceptions are lost and the caller continues too early.

```csharp
// BUG - fire-and-forget by accident
public async Task ProcessAsync()
{
    _repo.SaveAsync();          // not awaited
}

// FIX
public async Task ProcessAsync()
{
    await _repo.SaveAsync();
}
```

## Async Streams with IAsyncEnumerable

```csharp
public async IAsyncEnumerable<Order> StreamOrdersAsync(
    [EnumeratorCancellation] CancellationToken ct = default)
{
    await foreach (var order in _db.Orders.AsAsyncEnumerable().WithCancellation(ct))
        yield return order;
}
```
