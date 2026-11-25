# C# Type Safety and Modern Types

## Nullable Reference Types

Enable nullable reference types so the compiler warns when a possibly-null value is dereferenced.
Treat nullable warnings as errors in new projects.

```xml
<PropertyGroup>
  <Nullable>enable</Nullable>
  <WarningsAsErrors>nullable</WarningsAsErrors>
</PropertyGroup>
```

```csharp
public User? FindUser(int id) => _users.GetValueOrDefault(id);   // may return null

var user = FindUser(1);
Console.WriteLine(user.Name);        // warning CS8602: possible null dereference
Console.WriteLine(user?.Name ?? "unknown");
```

Avoid silencing warnings with the null-forgiving operator `!` unless you have proven the value is not null.

## Records for Data

Records give value equality, immutability with `init` properties and `with` expressions.
Use them for DTOs, messages and value objects.

```csharp
public record OrderDto(int Id, string Customer, decimal Total);

var a = new OrderDto(1, "Alice", 10m);
var b = a with { Total = 12m };   // copy with one change
Console.WriteLine(a == new OrderDto(1, "Alice", 10m));   // True: value equality
```

## Required and Init-Only Members

`required` (C# 11) forces callers to set a property in the object initializer; `init` makes it
settable only during construction.

```csharp
public class CreateUserRequest
{
    public required string Email { get; init; }
    public required string Name { get; init; }
    public string? Phone { get; init; }
}

var req = new CreateUserRequest { Email = "a@b.com", Name = "Alice" };   // compiles
// new CreateUserRequest { Name = "Alice" };   // error CS9035: required member 'Email' not set
```

## Generics with Constraints

Constraints let the compiler check what a type argument can do.

```csharp
public static T? FirstOrNull<T>(IEnumerable<T> items) where T : class =>
    items.FirstOrDefault();

public class Repository<TEntity> where TEntity : class, IEntity, new()
{
    public TEntity Create() => new TEntity();
}

// Generic math (.NET 7+)
public static T Sum<T>(IEnumerable<T> values) where T : INumber<T> =>
    values.Aggregate(T.Zero, (acc, v) => acc + v);
```

## Pattern Matching and Switch Expressions

Switch expressions are exhaustive-checked by the compiler and replace long if/else chains.

```csharp
public decimal Shipping(Order order) => order switch
{
    { Total: >= 100 } => 0m,
    { Country: "SK" or "CZ" } => 3.5m,
    { Weight: > 20 } => 25m,
    _ => 9.9m,
};

if (shape is Circle { Radius: > 0 } c)
    Console.WriteLine(c.Radius);
```

## Strongly-Typed IDs and Enums

Primitive obsession (using `int` or `string` for everything) lets you pass a `CustomerId` where an
`OrderId` is expected. Wrap identifiers in small record structs and use enums for fixed sets of values.

```csharp
public readonly record struct OrderId(Guid Value);
public readonly record struct CustomerId(Guid Value);

public Order Get(OrderId id) => ...;   // can't accidentally pass a CustomerId

public enum OrderStatus { Pending, Paid, Shipped, Cancelled }
```

## Avoid dynamic and object

`dynamic` turns off compile-time checking and moves errors to runtime. Prefer generics, interfaces
or `JsonElement` / typed DTOs when handling JSON.

```csharp
// BAD
dynamic data = JsonConvert.DeserializeObject(json);
var total = data.totla;   // typo found only at runtime

// GOOD
var order = JsonSerializer.Deserialize<OrderDto>(json);
var total2 = order!.Total;
```

## Immutable Collections

Expose read-only interfaces so callers can't modify internal state.

```csharp
public class Cart
{
    private readonly List<CartLine> _lines = [];
    public IReadOnlyList<CartLine> Lines => _lines;   // callers can't Add/Remove
    public void Add(CartLine line) => _lines.Add(line);
}
```
