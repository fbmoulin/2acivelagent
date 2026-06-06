# PR Review: Add missing infrastructure files and database schema

## Summary

This PR adds substantial infrastructure — a Flask API, Nginx config, PostgreSQL schema, Alembic migrations, CI/CD pipelines, and tests. The overall direction is solid, but there are several issues ranging from critical bugs to security concerns that should be addressed before merging.

---

## Critical Issues

### 1. Flask Development Server in Production

**File:** `scripts/python/app.py:943`

```python
app.run(host='0.0.0.0', port=5000)
```

The Flask built-in server is single-threaded and not suitable for production. The comment on line 941–942 acknowledges Gunicorn should be used, but the code still falls back to `app.run()`. The Dockerfile CMD also runs `python app.py` directly.

**Fix:** Replace `app.run()` with a Gunicorn invocation, and update the Dockerfile CMD accordingly:

```dockerfile
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "--timeout", "120", "app:app"]
```

---

### 2. Unit Test Suite Is Broken — Missing JWT Auth in Tests

**File:** `tests/unit/test_api_routes.py`, `tests/conftest.py`

All protected endpoints (`/extract-pdf`, `/firac-analysis`, `/datajud-search`, `/distinguish-analysis`, `/generate-document`) require JWT authentication via the `@require_auth` decorator. The `conftest.py` `client` fixture does not provide any JWT token, and none of the test requests include an `Authorization` header.

As a result, every test asserting a `200` or `400` response from a protected endpoint will actually receive a `401` and fail. For example:

```python
# test_api_routes.py:70 — will get 401, not 200
def test_extract_pdf_accepts_base64(self, client, sample_pdf_base64):
    response = client.post('/extract-pdf', ...)
    assert response.status_code == 200  # FAILS: gets 401
```

Similarly, `test_firac_requires_text` (expects 400) and `test_extract_pdf_requires_pdf_content` (expects 400) will both receive 401, not 400, because the auth check runs first.

**Fix:** Add a fixture to generate and inject a valid JWT token in the test client, or mock the `require_auth` decorator in unit tests:

```python
@pytest.fixture
def auth_headers():
    token = create_jwt_token(user_id='test_user', roles=['api'])
    return {'Authorization': f'Bearer {token}'}
```

---

## Security Issues

### 3. Timing Attack Vulnerability in API Key Comparison

**File:** `scripts/python/app.py:701`

```python
if not expected_key or api_key != expected_key:
```

String equality (`!=`) is not constant-time and is vulnerable to timing attacks. An attacker can measure response times to deduce the API key character by character.

**Fix:** Use `hmac.compare_digest()`:

```python
import hmac
if not expected_key or not hmac.compare_digest(api_key, expected_key):
```

---

### 4. Rate Limiting Missing for `/auth/token` Endpoint in Nginx

**File:** `infrastructure/nginx/nginx.conf`

`docs/SECURITY.md` documents an `auth_limit` zone with `rate=3r/m` applied to `/auth/`:

```nginx
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=3r/m;
location /auth/ { limit_req zone=auth_limit burst=5 nodelay; }
```

Neither the zone definition nor the location block exists in the actual `nginx.conf`. The `/auth/token` endpoint is only reachable via the `/api/` location block, which uses the general `api_limit` zone (10r/s) — far too permissive for a credential endpoint.

**Fix:** Add a dedicated rate-limit zone and location for `/api/auth/` with a stricter limit.

---

### 5. Dev Dependencies Included in Production Docker Image

**File:** `requirements.txt`, `infrastructure/docker/Dockerfile.python`

`requirements.txt` bundles production and development dependencies together (`pytest`, `black`, `isort`, `mypy`, `pre-commit`, `factory-boy`, `faker`). The Dockerfile installs the full `requirements.txt` in the production image.

This unnecessarily increases the attack surface of the production container and inflates image size.

**Fix:** Split into `requirements.txt` (prod) and `requirements-dev.txt` (dev), and only install the former in the Dockerfile.

---

### 6. Logging Format String Will Cause Errors for Non-filtered Loggers

**File:** `scripts/python/app.py:88–91`

```python
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s'
)
```

The `%(request_id)s` placeholder is injected by `RequestIdFilter`, which is only attached to the module-level `logger` instance (line 103). Log records from other loggers (e.g., Werkzeug, SQLAlchemy, the `redis` library) that share the same handler will raise a `KeyError`/`ValueError` because `request_id` is not set on their records.

**Fix:** Use `logging.Filter` as a handler-level filter, or use `logging.LoggerAdapter`, or provide a default with `%(request_id)s` safely by applying the filter at the handler instead of the logger.

---

## Bugs

### 7. `orgao_julgador` Parameter Silently Ignored

**File:** `scripts/python/app.py:427–461`

The `DatajudClient.search()` method processes `classe_codigo` and `texto_livre` from `query_params` but never reads `orgao_julgador`, despite it being documented in the API docs and OpenAPI spec as a supported parameter. The parameter is accepted but silently discarded.

---

### 8. OpenAI Model Hardcoded Instead of Using Config

**File:** `scripts/python/app.py:389, 540, 597`

All three AI service classes (`FIRACAnalyzer`, `DistinguishAnalyzer`, `DocumentGenerator`) hardcode `model="gpt-4"` instead of reading from `Config.OPENAI_MODEL`. The config class exposes this setting specifically for runtime customization, but it's never used.

```python
# Line 389 — should be Config.OPENAI_MODEL
model="gpt-4",
```

---

### 9. JSON Truncation May Produce Invalid JSON in LLM Prompt

**File:** `scripts/python/app.py:521`

```python
precedent_json = json.dumps(precedent_data, ensure_ascii=False)[:1500]
```

Slicing a JSON string at an arbitrary character boundary produces a syntactically invalid JSON fragment. This is then embedded directly in the LLM prompt as if it were valid JSON. The LLM may process the broken structure unexpectedly, or produce unpredictable results.

**Fix:** Truncate the data structure before serializing, not after:

```python
# Limit the data structure, then serialize
if isinstance(precedent_data, dict):
    precedent_json = json.dumps(
        {k: str(v)[:200] for k, v in list(precedent_data.items())[:10]},
        ensure_ascii=False
    )
```

---

### 10. Duplicate Dependency in `requirements.txt`

**File:** `requirements.txt:32,55`

`httpx==0.26.0` is listed twice — once under "HTTP & Async" (line 32) and again under "Testing (dev)" (line 55).

---

### 11. Naive Timestamps Throughout `app.py`

**File:** `scripts/python/app.py:341, 402, 551, 609, 637, 653`

`datetime.now()` produces naive (timezone-unaware) datetimes. Given that the database schema uses `TIMESTAMP WITH TIME ZONE` and the API responses include ISO timestamps, these should be timezone-aware.

**Fix:** Use `datetime.now(timezone.utc)` or `datetime.utcnow()` consistently (with a note that `utcnow()` is deprecated in Python 3.12+; prefer `datetime.now(timezone.utc)`).

---

## Database / Schema Issues

### 12. Schema Inconsistency Between `init_database.sql` and Alembic Migration

**Files:** `scripts/sql/init_database.sql:28,125`, `migrations/versions/20241204_000000_001_initial_schema.py:63`

The Alembic migration creates proper PostgreSQL ENUM types (`judicial.case_status`, `judicial.document_type`) and uses them for the `status` and `document_type` columns. The `init_database.sql` script (used for Docker container initialization) uses plain `VARCHAR(50)` for the same columns, creating a schema drift between the two initialization paths.

A deployment using the Docker init script will have a structurally different schema than one that ran Alembic migrations, making it impossible to run Alembic against a Docker-initialized database without conflicts.

**Fix:** Either make `init_database.sql` define and use the same ENUM types as the migration, or remove it in favor of Alembic as the single source of truth and document this explicitly.

---

### 13. `downgrade()` Drops Tables Without `IF EXISTS`

**File:** `migrations/versions/20241204_000000_001_initial_schema.py:276`

```python
op.drop_table('logs', schema='audit')
```

If the migration was partially applied (e.g., it failed mid-way through `upgrade()`), running `downgrade()` will raise an error because the table doesn't exist. All `op.drop_table()` calls in `downgrade()` should handle this gracefully.

---

### 14. `case_id` Foreign Key Nullable in Child Tables

**Files:** `migrations/versions/20241204_000000_001_initial_schema.py:84,107`

`documents.case_id` and `firac_analyses.case_id` are both `nullable=True`. This allows orphaned records — documents and analyses not associated with any case — which appears unintentional given the cascade delete behavior implies they are always case-owned.

---

## CI/CD Issues

### 15. `POETRY_VERSION` Defined but Poetry Never Installed or Used

**File:** `.github/workflows/ci.yml:14`

```yaml
env:
  POETRY_VERSION: '1.7.1'
```

The workflow declares a `POETRY_VERSION` global environment variable but all dependency installation steps use `pip install -r requirements.txt` directly. Poetry is never installed or invoked. The variable is dead configuration that creates misleading expectations.

---

### 16. `safety check` Is Deprecated

**File:** `.github/workflows/ci.yml` (security job)

```yaml
safety check -r requirements.txt --full-report
```

The `safety check` command was deprecated in Safety CLI v3.x in favor of `safety scan`. Using the deprecated command in CI will produce deprecation warnings and may break in future Safety versions.

**Fix:**

```yaml
safety scan -r requirements.txt
```

---

### 17. Test Coverage Threshold Too Low for a Judicial System

**File:** `.github/workflows/ci.yml` (coverage job)

```yaml
--cov-fail-under=50
```

A 50% minimum coverage is generally considered insufficient for a production system handling legal documents where correctness is critical. Consider raising this to at least 70–80% and tracking the improvement.

---

## Minor / Nits

- **`scripts/python/app.py:160`** — `generate_request_id()` returns only 8 hex characters of a UUID, providing 32 bits of entropy. For distributed tracing this is low; consider using the full UUID or at least 16 characters.

- **`docs/SECURITY.md`** — Mentions token revocation/blacklisting as a security recommendation, but there is no implementation of this in the codebase. If it's a future requirement, flag it explicitly as a TODO rather than presenting it as an existing capability.

- **`infrastructure/nginx/nginx.conf`** — Missing `Content-Security-Policy` header. `docs/SECURITY.md` shows a CSP example, but it's not applied in the actual nginx config.

- **`migrations/versions/20241204_000000_001_initial_schema.py:248`** — Uses the deprecated `language 'plpgsql'` quoted syntax. Modern PostgreSQL prefers `language plpgsql` (unquoted), though both work.
