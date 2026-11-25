# REST API Design in ASP.NET Core

## Resource Naming

Use plural nouns for resources and HTTP verbs for actions, not verbs in the URL.

```
# GOOD
GET    /api/v1/users
GET    /api/v1/users/123
POST   /api/v1/users
PUT    /api/v1/users/123
DELETE /api/v1/users/123

# BAD
GET  /getUser?id=123
POST /createUser
```

## Status Codes with TypedResults

Return the status code that matches the outcome. With minimal APIs, `TypedResults` and `Results<...>`
make the possible responses part of the method signature (and of the OpenAPI document).

```csharp
app.MapGet("/api/v1/users/{id:int}", async Task<Results<Ok<UserDto>, NotFound>> (
    int id, IUserService users, CancellationToken ct) =>
{
    var user = await users.GetAsync(id, ct);
    return user is null ? TypedResults.NotFound() : TypedResults.Ok(user);
});

app.MapPost("/api/v1/users", async (CreateUserRequest req, IUserService users, CancellationToken ct) =>
{
    var user = await users.CreateAsync(req, ct);
    return TypedResults.Created($"/api/v1/users/{user.Id}", user);
});
```

Common codes: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden,
404 Not Found, 409 Conflict, 422 Unprocessable Entity, 429 Too Many Requests, 500 Internal Server Error.

## Controllers and Validation

With `[ApiController]`, invalid models automatically return 400 with a `ValidationProblemDetails` body.

```csharp
[ApiController]
[Route("api/v1/[controller]")]
public class UsersController(IUserService users) : ControllerBase
{
    [HttpGet("{id:int}")]
    [ProducesResponseType<UserDto>(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<UserDto>> Get(int id, CancellationToken ct)
    {
        var user = await users.GetAsync(id, ct);
        return user is null ? NotFound() : Ok(user);
    }
}

public record CreateUserRequest([Required, EmailAddress] string Email, [Required, StringLength(100)] string Name);
```

## Error Responses with ProblemDetails

Use the standard RFC 7807 format for errors instead of custom shapes or raw exception messages.

```csharp
builder.Services.AddProblemDetails();
app.UseExceptionHandler();
app.UseStatusCodePages();

// Returning a problem from an endpoint
return TypedResults.Problem(
    title: "Insufficient stock",
    detail: $"Only {available} items of {sku} are available.",
    statusCode: StatusCodes.Status409Conflict);
```

## DTOs Instead of Entities

Never return EF Core entities directly: it leaks internal fields (password hashes, foreign keys),
can cause cycles during serialization, and ties your API contract to the database schema.

```csharp
// BAD
return await db.Users.FindAsync(id);

// GOOD
return await db.Users
    .Where(u => u.Id == id)
    .Select(u => new UserDto(u.Id, u.Name, u.Email))
    .FirstOrDefaultAsync(ct);
```

## Versioning

Version the API from day one. URL versioning is the most discoverable; the `Asp.Versioning.Http`
(minimal APIs) and `Asp.Versioning.Mvc` (controllers) packages add version routing and reporting.

```
/api/v1/users
/api/v2/users
```

## Pagination

Never return unbounded lists. Accept `page`/`pageSize` (or a cursor) with a maximum page size.

```csharp
app.MapGet("/api/v1/orders", async (int page, int pageSize, AppDbContext db, CancellationToken ct) =>
{
    pageSize = Math.Clamp(pageSize, 1, 100);
    var items = await db.Orders.OrderBy(o => o.Id)
        .Skip((page - 1) * pageSize).Take(pageSize)
        .Select(o => new OrderDto(o.Id, o.Total))
        .ToListAsync(ct);
    return TypedResults.Ok(new { data = items, page, pageSize });
});
```

## Authentication

Send tokens in the `Authorization: Bearer` header. Never put secrets or tokens in the URL query string;
URLs end up in server, proxy and browser logs.

```csharp
builder.Services.AddAuthentication().AddJwtBearer();
builder.Services.AddAuthorization();

app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/api/v1/me", (ClaimsPrincipal user) => user.Identity?.Name).RequireAuthorization();
```

## Rate Limiting

ASP.NET Core (.NET 7+) has built-in rate limiting middleware. Set the rejection status to 429.

```csharp
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddFixedWindowLimiter("api", o =>
    {
        o.PermitLimit = 100;
        o.Window = TimeSpan.FromMinutes(1);
    });
});

app.UseRateLimiter();
app.MapGroup("/api/v1").RequireRateLimiting("api");
```

## Idempotency

POST endpoints that create payments or orders should accept an idempotency key so clients can retry
safely without creating duplicates.

```
POST /api/v1/payments
Idempotency-Key: 6f1c2a9e-0d4b-4e8a-9a4f-1c2b3d4e5f60
```
