# Python Security Best Practices

## SQL Injection Prevention

SQL injection is one of the most critical vulnerabilities in web applications.
Never concatenate user input directly into SQL queries.

### Vulnerable Pattern
```python
# DANGEROUS - never do this
query = "SELECT * FROM users WHERE name = '" + user_input + "'"
cursor.execute(query)
```

### Safe Pattern
```python
# SAFE - use parameterized queries
query = "SELECT * FROM users WHERE name = %s"
cursor.execute(query, (user_input,))

# With SQLAlchemy ORM
user = session.query(User).filter(User.name == user_input).first()
```

## Command Injection

Avoid passing unsanitized input to shell commands.

```python
# DANGEROUS
import os
os.system("ls " + user_input)

# SAFE
import subprocess
subprocess.run(["ls", user_input], shell=False, capture_output=True)
```

## Hardcoded Secrets

Never hardcode API keys, passwords, or tokens in source code.

```python
# DANGEROUS
API_KEY = "sk-abc123secret"
DB_PASSWORD = "hunter2"

# SAFE
import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.environ["API_KEY"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
```

## Insecure Deserialization

```python
# DANGEROUS - pickle can execute arbitrary code
import pickle
data = pickle.loads(user_provided_bytes)

# SAFE - use json for untrusted data
import json
data = json.loads(user_provided_string)
```

## Path Traversal

```python
# DANGEROUS
def read_file(filename):
    with open("/uploads/" + filename) as f:
        return f.read()

# SAFE
import os
def read_file(filename):
    base = "/uploads"
    path = os.path.realpath(os.path.join(base, filename))
    if not path.startswith(base):
        raise ValueError("Path traversal detected")
    with open(path) as f:
        return f.read()
```

## References
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Python Security: https://python.org/dev/security/
- CWE-89: SQL Injection
- CWE-78: OS Command Injection
- CWE-22: Path Traversal
