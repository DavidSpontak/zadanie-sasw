# C# Design Patterns

## Dependency Injection in ASP.NET Core

Register services in the built-in container and receive them through constructors.
No `new` for dependencies and no static service locators, which makes classes testable.

```csharp
builder.Services.AddScoped<IOrderRepository, SqlOrderRepository>();
builder.Services.AddScoped<OrderService>();

public class OrderService(IOrderRepository orders, ILogger<OrderService> logger)
{
    public async Task<Order?> GetAsync(int id) => await orders.GetByIdAsync(id);
}
```

## Service Lifetimes

- **Transient**: new instance every time it is requested (lightweight, stateless services)
- **Scoped**: one instance per HTTP request (DbContext, unit of work)
- **Singleton**: one instance for the app lifetime (caches, configuration, HttpClient handlers)

Never inject a scoped service into a singleton ("captive dependency"): the scoped object then lives
forever, e.g. a DbContext shared across requests. ASP.NET Core detects this in Development.

```csharp
// BAD - singleton captures a scoped DbContext
builder.Services.AddSingleton<ReportCache>();   // ReportCache(AppDbContext db)

// GOOD - create a scope when needed
public class ReportCache(IServiceScopeFactory scopes)
{
    public async Task RefreshAsync()
    {
        using var scope = scopes.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        // ...
    }
}
```

## Strategy Pattern

Replace if/else or switch chains over a "type" string with one class per behavior behind an interface.
This follows the Open/Closed Principle: new channels don't change existing code.

```csharp
// BEFORE - every new channel edits this method
public void Send(User user, string message, string channel)
{
    if (channel == "email") _smtp.Send(user.Email, message);
    else if (channel == "sms") _sms.Send(user.Phone, message);
    else if (channel == "push") _push.Send(user.DeviceId, message);
}

// AFTER - strategies registered in DI
public interface INotificationChannel
{
    string Name { get; }
    Task SendAsync(User user, string message);
}

public class EmailChannel(ISmtpClient smtp) : INotificationChannel
{
    public string Name => "email";
    public Task SendAsync(User user, string message) => smtp.SendAsync(user.Email, message);
}

public class Notifier(IEnumerable<INotificationChannel> channels)
{
    public Task SendAsync(User user, string message, string channel) =>
        channels.Single(c => c.Name == channel).SendAsync(user, message);
}
```

## Keyed Services (.NET 8+)

Resolve one of several implementations of the same interface by key.

```csharp
builder.Services.AddKeyedSingleton<INotificationChannel, EmailChannel>("email");
builder.Services.AddKeyedSingleton<INotificationChannel, SmsChannel>("sms");

public class AlertService([FromKeyedServices("sms")] INotificationChannel sms) { }
```

## Factory Pattern

Use a factory when creation logic is non-trivial or depends on runtime data.

```csharp
public interface IPaymentProcessor { Task PayAsync(decimal amount); }

public class PaymentProcessorFactory(IServiceProvider services)
{
    public IPaymentProcessor Create(PaymentMethod method) => method switch
    {
        PaymentMethod.Card => services.GetRequiredService<CardProcessor>(),
        PaymentMethod.PayPal => services.GetRequiredService<PayPalProcessor>(),
        _ => throw new ArgumentOutOfRangeException(nameof(method)),
    };
}
```

## Options Pattern for Configuration

Bind configuration sections to typed classes instead of reading strings from `IConfiguration` everywhere,
and validate them at startup.

```csharp
public class SmtpOptions
{
    [Required] public string Host { get; set; } = "";
    [Range(1, 65535)] public int Port { get; set; } = 587;
}

builder.Services.AddOptions<SmtpOptions>()
    .Bind(builder.Configuration.GetSection("Smtp"))
    .ValidateDataAnnotations()
    .ValidateOnStart();

public class EmailSender(IOptions<SmtpOptions> options)
{
    private readonly SmtpOptions _smtp = options.Value;
}
```

## Decorator Pattern

Add behavior (caching, logging, retries) around an existing implementation without changing it.

```csharp
public class CachedProductRepository(IProductRepository inner, IMemoryCache cache) : IProductRepository
{
    public Task<Product?> GetAsync(int id) =>
        cache.GetOrCreateAsync($"product:{id}", _ => inner.GetAsync(id));
}
```

## Parameter Object (avoiding long parameter lists)

```csharp
// BAD - 7 parameters, easy to mix up
public void CreateInvoice(int customerId, int orderId, decimal amount, string currency,
                          DateTime dueDate, string notes, bool sendEmail) { }

// GOOD
public record CreateInvoiceCommand(int CustomerId, int OrderId, Money Amount, DateOnly DueDate,
                                   string? Notes = null, bool SendEmail = true);

public void CreateInvoice(CreateInvoiceCommand command) { }
```
