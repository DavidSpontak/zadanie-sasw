# Error Handling and Logging in C#

## Structured Logging with ILogger

Use `ILogger<T>` with message templates. Placeholders become searchable fields in structured log sinks
(Serilog, Application Insights, Seq). String interpolation loses the structure and always allocates.

```csharp
// BAD - interpolation: one opaque string, built even if the level is disabled
_logger.LogInformation($"User {userId} placed order {orderId}");

// GOOD - message template with named placeholders
_logger.LogInformation("User {UserId} placed order {OrderId}", userId, orderId);

// Always pass the exception as the first argument
_logger.LogError(ex, "Failed to process order {OrderId}", orderId);
```

## High-Performance Logging with LoggerMessage

For hot paths, the `[LoggerMessage]` source generator (.NET 6+) avoids boxing and parsing templates.

```csharp
public static partial class Log
{
    [LoggerMessage(Level = LogLevel.Information, Message = "Order {OrderId} shipped to {Country}")]
    public static partial void OrderShipped(ILogger logger, int orderId, string country);
}

Log.OrderShipped(_logger, order.Id, order.Country);
```

## Log Levels

- `Trace` / `Debug`: diagnostic detail, off in production
- `Information`: normal business events (order placed, user signed in)
- `Warning`: unexpected but handled (retrying, fallback used)
- `Error`: an operation failed
- `Critical`: the application can't continue

Never log secrets, passwords, tokens or full credit card numbers.

## Custom Exception Hierarchy

Define exceptions for your domain so callers can catch specific failures.

```csharp
public class AppException : Exception
{
    public AppException(string message, Exception? inner = null) : base(message, inner) { }
}

public class NotFoundException(string resource, object id)
    : AppException($"{resource} with id '{id}' was not found");

public class ValidationException(string field, string message)
    : AppException($"Validation failed for '{field}': {message}")
{
    public string Field { get; } = field;
}
```

## Exception Filters

`when` filters catch an exception only if a condition is true, without unwinding the stack otherwise.

```csharp
try
{
    await _http.GetStringAsync(url);
}
catch (HttpRequestException ex) when (ex.StatusCode == HttpStatusCode.NotFound)
{
    return null;
}
```

## Global Exception Handling and ProblemDetails

In ASP.NET Core, handle unexpected exceptions in one place and return RFC 7807 ProblemDetails
instead of stack traces.

```csharp
builder.Services.AddProblemDetails();
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();   // .NET 8+

app.UseExceptionHandler();

public class GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext ctx, Exception ex, CancellationToken ct)
    {
        var status = ex is NotFoundException ? StatusCodes.Status404NotFound : StatusCodes.Status500InternalServerError;
        if (status == 500) logger.LogError(ex, "Unhandled exception");
        ctx.Response.StatusCode = status;
        await ctx.Response.WriteAsJsonAsync(new ProblemDetails { Status = status, Title = ex.Message }, ct);
        return true;
    }
}
```

## Retry and Circuit Breaker

Transient failures (timeouts, 5xx, 429) should be retried with exponential backoff, and a circuit
breaker should stop calling a dependency that keeps failing. Use Polly or
`Microsoft.Extensions.Http.Resilience` rather than hand-written loops.

```csharp
// .NET 8+: standard pipeline = rate limiter, total timeout, retry, circuit breaker, attempt timeout
builder.Services.AddHttpClient<PaymentClient>()
    .AddStandardResilienceHandler();

// Custom Polly pipeline
var pipeline = new ResiliencePipelineBuilder()
    .AddRetry(new RetryStrategyOptions
    {
        MaxRetryAttempts = 3,
        BackoffType = DelayBackoffType.Exponential,
        UseJitter = true,
        ShouldHandle = new PredicateBuilder().Handle<HttpRequestException>(),
    })
    .AddCircuitBreaker(new CircuitBreakerStrategyOptions
    {
        FailureRatio = 0.5,
        MinimumThroughput = 10,
        BreakDuration = TimeSpan.FromSeconds(30),
    })
    .Build();

await pipeline.ExecuteAsync(async ct => await CallExternalApiAsync(ct), cancellationToken);
```

## Result Pattern for Expected Failures

Exceptions are for unexpected situations. For expected outcomes (validation failed, not found),
return a result type instead of throwing; it is cheaper and makes the failure explicit in the signature.

```csharp
public record Result<T>(T? Value, string? Error)
{
    public bool IsSuccess => Error is null;
    public static Result<T> Ok(T value) => new(value, null);
    public static Result<T> Fail(string error) => new(default, error);
}

public Result<Email> ParseEmail(string input) =>
    input.Contains('@') ? Result<Email>.Ok(new Email(input)) : Result<Email>.Fail("Invalid email");
```
