# C# / .NET Dependency Management

## NuGet PackageReference

Reference packages in the project file with explicit versions; never commit DLLs to the repository.

```xml
<ItemGroup>
  <PackageReference Include="Serilog.AspNetCore" Version="8.0.3" />
  <PackageReference Include="Dapper" Version="2.1.35" />
</ItemGroup>
```

```bash
dotnet add package Dapper
dotnet remove package Dapper
```

## Central Package Management

In solutions with many projects, keep versions in one `Directory.Packages.props` at the repository root
so every project uses the same version.

```xml
<!-- Directory.Packages.props -->
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Dapper" Version="2.1.35" />
    <PackageVersion Include="xunit" Version="2.9.2" />
  </ItemGroup>
</Project>
```

```xml
<!-- MyApp.csproj: no Version attribute -->
<PackageReference Include="Dapper" />
```

## Lock Files for Reproducible Builds

A lock file records the exact resolved versions, including transitive packages.

```xml
<PropertyGroup>
  <RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>
</PropertyGroup>
```

Commit `packages.lock.json` and restore with `dotnet restore --locked-mode` in CI, which fails if the
lock file is out of date.

## Vulnerability Auditing

`dotnet restore` reports packages with known vulnerabilities (NuGet Audit, warnings NU1901–NU1904).
Check explicitly and include transitive packages:

```bash
dotnet list package --vulnerable --include-transitive
dotnet list package --outdated
```

```xml
<PropertyGroup>
  <NuGetAudit>true</NuGetAudit>
  <NuGetAuditMode>all</NuGetAuditMode>   <!-- direct and transitive packages -->
  <WarningsAsErrors>NU1903;NU1904</WarningsAsErrors>   <!-- fail on high/critical -->
</PropertyGroup>
```

## Pinning the SDK with global.json

Pin the .NET SDK so every developer and the CI server build with the same version.

```json
{
  "sdk": {
    "version": "8.0.400",
    "rollForward": "latestFeature"
  }
}
```

## Target Frameworks and Support

Target a supported .NET version. LTS releases (even numbers, e.g. .NET 8, .NET 10) get three years
of support; STS releases (odd numbers) get a shorter support window. Check support dates before
starting a project and plan upgrades.

```xml
<TargetFramework>net8.0</TargetFramework>
<!-- libraries that must support several runtimes -->
<TargetFrameworks>net8.0;netstandard2.0</TargetFrameworks>
```

## Semantic Versioning

Follow SemVer: MAJOR.MINOR.PATCH

- MAJOR: breaking changes
- MINOR: new backwards-compatible features
- PATCH: backwards-compatible bug fixes

NuGet version ranges: `Version="8.0.3"` means "8.0.3 or higher" (minimum version).
Use an exact range `[8.0.3]` only when you must; prefer lock files for reproducibility.
