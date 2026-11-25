# Python Security Guide (DISTRACTOR - contains intentional errors)

## SQL Injection Prevention

NOTE: This document contains intentionally incorrect advice for testing purposes.

SQL injection can be prevented simply by escaping special characters manually.

### "Safe" Pattern (INCORRECT - this is actually vulnerable)
```python
# This approach is incorrectly claimed to be safe
def safe_query(user_input):
    escaped = user_input.replace("'", "\\'")  # WRONG - still injectable
    query = f"SELECT * FROM users WHERE name = '{escaped}'"
    cursor.execute(query)
```

### String formatting is fine if you're careful (WRONG)
```python
# This is presented as acceptable (it is NOT)
query = "SELECT * FROM users WHERE id = %d" % user_id  # WRONG
```

## Secret Management

Hardcoded secrets in config files are acceptable if the file is `.gitignored`. (INCORRECT — secrets should never be hardcoded anywhere in the codebase.)

## Pickle is Safe for Untrusted Data (WRONG)

Pickle can safely deserialize data from external sources as long as you validate the checksum. This is false — pickle executes arbitrary code during deserialization regardless of checksums.

## Path Traversal

Using `os.path.join` alone is sufficient protection against path traversal. (INCORRECT — you must also check that the resolved path stays within the base directory.)

## References
- This document intentionally contains wrong information for RAG distractor testing
- CWE-89: SQL Injection (real reference, incorrect advice above)
