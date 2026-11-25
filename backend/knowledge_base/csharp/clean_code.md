# Clean Code & Maintainability in C#

## Single Responsibility Principle (SRP)

Each class or method should have exactly one reason to change.

```csharp
// VIOLATION - one method validates, saves, emails and updates stock
public async Task ProcessOrderAsync(Order order)
{
    if (order.CustomerId == 0) throw new ArgumentException("Missing customer");
    _db.Orders.Add(order);
    await _db.SaveChangesAsync();
    await _email.SendAsync(order.Email, "Order confirmed");
    foreach (var line in order.Lines) _inventory.Decrement(line.Sku, line.Quantity);
}

// GOOD - separated concerns, composed by a coordinator
public async Task ProcessOrderAsync(Order order)
{
    _validator.Validate(order);
    await _orders.SaveAsync(order);
    await _notifier.OrderConfirmedAsync(order);
    await _inventory.ReserveAsync(order.Lines);
}
```

## DRY: Don't Repeat Yourself

Duplicated code creates a maintenance burden and inconsistency risk. Extract the shared part.

```csharp
// WET
public Task<List<User>> GetAdminsAsync() =>
    _db.Users.Where(u => u.Role == Role.Admin && !u.IsDeleted).ToListAsync();
public Task<List<User>> GetEditorsAsync() =>
    _db.Users.Where(u => u.Role == Role.Editor && !u.IsDeleted).ToListAsync();

// DRY
public Task<List<User>> GetByRoleAsync(Role role) =>
    _db.Users.Where(u => u.Role == role && !u.IsDeleted).ToListAsync();
```

## Naming Conventions

- Classes, records, structs, methods, properties, constants: `PascalCase`
- Interfaces: `I` prefix (`IUserRepository`)
- Parameters and local variables: `camelCase`
- Private fields: `_camelCase`
- Async methods: `Async` suffix (`GetUserAsync`)
- Avoid abbreviations and single-letter names except loop counters and lambdas

## Magic Numbers and Constants

```csharp
// BAD
if (response.StatusCode == (HttpStatusCode)429) await Task.Delay(86400000);

// GOOD
private const int OneDayMilliseconds = 24 * 60 * 60 * 1000;
if (response.StatusCode == HttpStatusCode.TooManyRequests) await Task.Delay(OneDayMilliseconds);
```

## Guard Clauses

Validate arguments at the top of a method and return early instead of nesting.

```csharp
public void Register(string email, User? referrer)
{
    ArgumentException.ThrowIfNullOrWhiteSpace(email);   // .NET 8+
    ArgumentNullException.ThrowIfNull(referrer);          // .NET 6+

    if (_users.Exists(email)) return;
    _users.Add(new User(email, referrer.Id));
}
```

## Disposing Resources with using

Types that implement `IDisposable` (streams, connections, commands) must be disposed, even when an
exception is thrown. Use `using` declarations or statements instead of calling `Dispose()` by hand.

```csharp
// BAD - leaks the file handle if ReadToEnd throws
var reader = new StreamReader(path);
var text = reader.ReadToEnd();
reader.Dispose();

// GOOD - C# 8 using declaration, disposed at end of scope
using var reader2 = new StreamReader(path);
var text2 = reader2.ReadToEnd();

// Async disposables
await using var connection = new SqlConnection(connString);
```

## Exception Handling

Catch specific exceptions, never swallow them silently, and rethrow with `throw;` to keep the stack trace.

```csharp
// BAD - swallows everything
try { ProcessPayment(); }
catch (Exception) { }

// BAD - 'throw ex;' resets the stack trace
catch (Exception ex) { _logger.LogError(ex, "Failed"); throw ex; }

// GOOD
try { ProcessPayment(); }
catch (PaymentDeclinedException ex)
{
    _logger.LogWarning(ex, "Payment declined for order {OrderId}", orderId);
    return PaymentResult.Declined;
}
catch (HttpRequestException ex)
{
    _logger.LogError(ex, "Payment provider unreachable");
    throw;   // preserves the original stack trace
}
```

## XML Documentation Comments

Document public APIs with XML comments; they show up in IntelliSense and generated docs.

```csharp
/// <summary>Calculates the discounted price.</summary>
/// <param name="price">Original price. Must be non-negative.</param>
/// <param name="discountPercent">Discount between 0 and 100.</param>
/// <returns>The final price after discount.</returns>
/// <exception cref="ArgumentOutOfRangeException">If an argument is out of range.</exception>
public static decimal ApplyDiscount(decimal price, decimal discountPercent)
{
    ArgumentOutOfRangeException.ThrowIfNegative(price);
    if (discountPercent is < 0 or > 100) throw new ArgumentOutOfRangeException(nameof(discountPercent));
    return price * (1 - discountPercent / 100);
}
```

## Code Complexity Metrics

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Cyclomatic Complexity | ≤5 | 6–10 | >10 |
| Method length (lines) | ≤20 | 21–50 | >50 |
| Parameter count | ≤3 | 4–5 | >5 |
| Nesting depth | ≤3 | 4 | >4 |

Enable the .NET code analyzers (`<AnalysisLevel>latest-recommended</AnalysisLevel>`) and treat warnings
as errors in CI (`<TreatWarningsAsErrors>true</TreatWarningsAsErrors>`).
