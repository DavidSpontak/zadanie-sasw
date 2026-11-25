# C# Testing Best Practices

## Unit Test Structure: AAA Pattern

Every test should follow Arrange → Act → Assert. Examples use xUnit; NUnit and MSTest follow the same ideas.

```csharp
public class CalculatorTests
{
    [Fact]
    public void Divide_PositiveNumbers_ReturnsQuotient()
    {
        // Arrange
        var calculator = new Calculator();

        // Act
        var result = calculator.Divide(10, 2);

        // Assert
        Assert.Equal(5, result);
    }

    [Fact]
    public void Divide_ByZero_ThrowsDivideByZeroException()
    {
        var calculator = new Calculator();
        Assert.Throws<DivideByZeroException>(() => calculator.Divide(10, 0));
    }
}
```

## Parameterized Tests

Use `[Theory]` with `[InlineData]` (or `[MemberData]` for complex inputs) instead of copy-pasting tests.

```csharp
[Theory]
[InlineData("hello", "HELLO")]
[InlineData("World", "WORLD")]
[InlineData("", "")]
public void ToUpper_ReturnsUppercase(string input, string expected)
{
    Assert.Equal(expected, input.ToUpperInvariant());
}
```

## Testing Async Code

Make the test method `async Task` and await the code under test. Never use `.Result` in tests.

```csharp
[Fact]
public async Task GetUserAsync_UnknownId_ThrowsNotFound()
{
    var service = new UserService(new InMemoryUserRepository());

    await Assert.ThrowsAsync<NotFoundException>(() => service.GetUserAsync(42));
}
```

## Mocking Dependencies

Depend on interfaces and inject them, so tests can replace them with mocks (Moq or NSubstitute).

```csharp
// NSubstitute
var repo = Substitute.For<IUserRepository>();
repo.GetByIdAsync(1).Returns(new User(1, "Alice"));
var service = new UserService(repo);

var user = await service.GetUserAsync(1);

Assert.Equal("Alice", user.Name);
await repo.Received(1).GetByIdAsync(1);

// Moq
var mock = new Mock<IUserRepository>();
mock.Setup(r => r.GetByIdAsync(1)).ReturnsAsync(new User(1, "Alice"));
mock.Verify(r => r.GetByIdAsync(1), Times.Once);
```

## Mocking HttpClient and Time

Don't mock `HttpClient` directly; give it a fake `HttpMessageHandler`. For time, inject
`TimeProvider` (.NET 8+) instead of calling `DateTime.UtcNow`.

```csharp
public class StubHandler(HttpStatusCode status, string body) : HttpMessageHandler
{
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct) =>
        Task.FromResult(new HttpResponseMessage(status) { Content = new StringContent(body) });
}

var http = new HttpClient(new StubHandler(HttpStatusCode.OK, "{\"temp\":22}"))
{
    BaseAddress = new Uri("https://api.example.com")
};
var client = new WeatherClient(http);
```

## Integration Tests with WebApplicationFactory

`WebApplicationFactory<Program>` (package `Microsoft.AspNetCore.Mvc.Testing`) runs the real app in memory.
With top-level statements, add `public partial class Program { }` to make `Program` visible to tests.

```csharp
public class UsersApiTests(WebApplicationFactory<Program> factory)
    : IClassFixture<WebApplicationFactory<Program>>
{
    [Fact]
    public async Task GetUser_Unknown_Returns404()
    {
        var client = factory.CreateClient();

        var response = await client.GetAsync("/api/v1/users/999");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }
}
```

## Test Coverage

- Aim for ≥80% line coverage as a baseline; 100% coverage does not mean correct tests.
- Collect coverage with coverlet: `dotnet test --collect:"XPlat Code Coverage"`
- Generate an HTML report with ReportGenerator.

## Test Project Organization

```
src/
  MyApp/
tests/
  MyApp.UnitTests/          # fast, no I/O, mocked dependencies
  MyApp.IntegrationTests/   # real database (e.g. Testcontainers), WebApplicationFactory
```

## Anti-Patterns to Avoid

1. **Testing implementation details** (private methods, call order) instead of behavior
2. **Shared mutable state** between tests: xUnit creates a new class instance per test, so use the constructor for setup
3. **Thread.Sleep in tests**: use fakes for time (`TimeProvider`) and await tasks
4. **Brittle assertions** on full exception messages or log text
5. **Not testing edge cases**: null, empty collections, boundary values

## Test Naming Convention

`MethodName_Scenario_ExpectedResult`

```csharp
public void Divide_ByZero_ThrowsDivideByZeroException() { }
public void CreateUser_DuplicateEmail_ReturnsConflict() { }
public void GetActiveUsers_MixedUsers_ReturnsOnlyActive() { }
```
