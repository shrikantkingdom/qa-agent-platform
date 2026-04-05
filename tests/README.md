# tests/

## Structure

```
tests/
├── __init__.py
├── conftest.py        # Shared fixtures (async client, test app)
├── test_health.py     # Smoke tests (health, config, providers)
└── README.md
```

## Running Tests

```bash
# All tests
make test

# Verbose
pytest tests/ -v

# Specific file
pytest tests/test_health.py -v
```

## Adding Tests

1. Create `tests/test_<module>.py`
2. Use the `client` fixture from `conftest.py` for async HTTP tests
3. Mark async tests with `@pytest.mark.anyio`
