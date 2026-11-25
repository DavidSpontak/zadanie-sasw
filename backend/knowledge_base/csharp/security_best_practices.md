# C# Security Best Practices

## SQL Injection Prevention

SQL injection happens when user input is concatenated or interpolated into a SQL string.
Never build SQL with `+`, `string.Format` or `$"..."` and pass it to the database as raw text.

### Vulnerable Pattern
```csharp
// DANGEROUS - never do this
var sql = "SELECT * FROM Users WHERE Name = '" + name + "'";
using var cmd = new SqlCommand(sql, connection);

// ALSO DANGEROUS - FromSqlRaw with interpolation is NOT parameterized
var users = db.Users.FromSqlRaw($"SELECT * FROM Users WHERE Name = '{name}'").ToList();
```

### Safe Pattern
```csharp
// ADO.NET - parameters
using var cmd = new SqlCommand("SELECT * FROM Users WHERE Name = @name", connection);
cmd.Parameters.Add("@name", SqlDbType.NVarChar, 100).Value = name;

// Dapper - anonymous object parameters
var users = await connection.QueryAsync<User>(
    "SELECT * FROM Users WHERE Name = @Name", new { Name = name });

// EF Core - LINQ, or FromSql with an interpolated string (converted to parameters)
var user = await db.Users.FirstOrDefaultAsync(u => u.Name == name);
var users2 = db.Users.FromSql($"SELECT * FROM Users WHERE Name = {name}").ToList();
```

## Command Injection

Never build a command line from user input. Pass arguments individually with `ArgumentList`
and do not run through a shell (`cmd.exe /c`, `/bin/sh -c`).

```csharp
// DANGEROUS
Process.Start("cmd.exe", "/c dir " + userInput);

// SAFE
var psi = new ProcessStartInfo("git") { UseShellExecute = false };
psi.ArgumentList.Add("log");
psi.ArgumentList.Add(userInput);   // passed as one argument, not parsed by a shell
using var process = Process.Start(psi);
```

## Hardcoded Secrets

Never hardcode API keys, passwords or connection strings with passwords in source code
or in a committed appsettings.json.

```csharp
// DANGEROUS
const string ApiKey = "sk-abc123secret";
var conn = "Server=db;Database=App;User Id=sa;Password=hunter2;";

// SAFE - read from configuration (User Secrets in development,
// environment variables or Azure Key Vault in production)
var apiKey = builder.Configuration["ExternalApi:ApiKey"];
var connString = builder.Configuration.GetConnectionString("Default");
```

In development use `dotnet user-secrets set "ExternalApi:ApiKey" "<value>"`, which stores
secrets outside the project folder.

## Insecure Deserialization

`BinaryFormatter`, `SoapFormatter`, `NetDataContractSerializer` and `LosFormatter` can execute
attacker-controlled code during deserialization. BinaryFormatter was removed from the runtime in .NET 9.
With Newtonsoft.Json, `TypeNameHandling` other than `None` lets JSON choose which type is created.

```csharp
// DANGEROUS
var obj = new BinaryFormatter().Deserialize(stream);
var settings = new JsonSerializerSettings { TypeNameHandling = TypeNameHandling.All };

// SAFE - System.Text.Json into a known type
var order = JsonSerializer.Deserialize<OrderDto>(json);
```

## Path Traversal

`Path.Combine` alone does not protect you: `../` segments still escape the folder, and if the second
argument is an absolute path, `Path.Combine` returns it unchanged.

```csharp
// DANGEROUS
var text = File.ReadAllText("/uploads/" + fileName);

// SAFE
var baseDir = Path.GetFullPath("/uploads") + Path.DirectorySeparatorChar;
var fullPath = Path.GetFullPath(Path.Combine(baseDir, fileName));
if (!fullPath.StartsWith(baseDir, StringComparison.Ordinal))
    throw new UnauthorizedAccessException("Path traversal detected");
var text = File.ReadAllText(fullPath);
```

## Password Hashing

Never store passwords in plain text or hash them with MD5, SHA1 or a single SHA256 pass.
Use a slow, salted algorithm: ASP.NET Core Identity's `PasswordHasher<TUser>` or PBKDF2.

```csharp
// DANGEROUS
var hash = Convert.ToHexString(MD5.HashData(Encoding.UTF8.GetBytes(password)));

// SAFE - PBKDF2 with a random salt
byte[] salt = RandomNumberGenerator.GetBytes(16);
byte[] hash = Rfc2898DeriveBytes.Pbkdf2(password, salt, 600_000, HashAlgorithmName.SHA256, 32);
// Compare with CryptographicOperations.FixedTimeEquals(...)
```

## Cross-Site Scripting (XSS)

Razor encodes output by default. `Html.Raw` and `MarkupString` turn encoding off, so never use
them with user input.

```csharp
// DANGEROUS (Razor)
@Html.Raw(Model.Comment)

// SAFE
@Model.Comment
```

## References
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- .NET security guidance: https://learn.microsoft.com/dotnet/standard/security/
- CWE-89: SQL Injection
- CWE-78: OS Command Injection
- CWE-22: Path Traversal
- CWE-502: Deserialization of Untrusted Data
