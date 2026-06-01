# Sistema de Automacao Juridica - Migration Environment Unit Tests
# Tests for migrations/env.py get_url() function and initial schema metadata.

import os
import pytest
from unittest.mock import patch

# We test get_url() in isolation by importing it directly.
# The module-level alembic code (context.is_offline_mode() etc.) runs only
# when alembic invokes the module, so we patch the context at import time.

# Patch alembic context before importing env so the module-level lines
# (context.is_offline_mode()) don't execute.
import sys
from unittest.mock import MagicMock

# Provide a mock alembic.context before importing migrations.env
_mock_context = MagicMock()
_mock_context.is_offline_mode.return_value = False
_mock_context.config.config_file_name = None
_mock_context.config.get_section.return_value = {"sqlalchemy.url": ""}
_mock_context.config.config_ini_section = "alembic"

# Patch alembic.context in sys.modules so migrations.env uses it
_alembic_mock = MagicMock()
_alembic_mock.context = _mock_context
sys.modules.setdefault("alembic", _alembic_mock)
sys.modules.setdefault("alembic.context", _mock_context)

# Also ensure sqlalchemy and pool are importable (they should be installed)
# Now import get_url from migrations.env
# We must do this carefully to avoid executing alembic's online mode
# during import. We directly import the function.
import importlib
import types


def _import_get_url():
    """Import get_url from migrations/env.py in isolation."""
    # Read the source and extract only the get_url function
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "migrations",
        "env.py",
    )
    with open(env_path) as f:
        source = f.read()

    # Create a minimal module namespace
    module = types.ModuleType("migrations_env_test")
    module.__file__ = env_path

    # We need to exec only enough to define get_url
    # Extract lines up to (and including) get_url definition
    lines = source.splitlines()
    # Find the end of get_url by looking for the next top-level def/class
    in_get_url = False
    extracted_lines = [
        "import os",
    ]
    for line in lines:
        if line.startswith("def get_url"):
            in_get_url = True
        if in_get_url:
            # Stop before the next top-level function/class definition
            if line.startswith("def ") and "get_url" not in line:
                break
            extracted_lines.append(line)

    exec("\n".join(extracted_lines), module.__dict__)
    return module.get_url


get_url = _import_get_url()


class TestGetUrl:
    """Tests for the get_url() function in migrations/env.py."""

    @pytest.mark.unit
    def test_returns_database_url_when_set(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://u:p@host/db"}, clear=False):
            result = get_url()
            assert result == "postgresql://u:p@host/db"

    @pytest.mark.unit
    def test_returns_postgres_url_when_database_url_unset(self):
        env = {"POSTGRES_URL": "postgresql://u2:p2@host2/db2"}
        # Ensure DATABASE_URL is not set
        with patch.dict(os.environ, env, clear=False):
            # Remove DATABASE_URL if present
            saved = os.environ.pop("DATABASE_URL", None)
            try:
                result = get_url()
                assert result == "postgresql://u2:p2@host2/db2"
            finally:
                if saved is not None:
                    os.environ["DATABASE_URL"] = saved

    @pytest.mark.unit
    def test_database_url_takes_precedence_over_postgres_url(self):
        env = {
            "DATABASE_URL": "postgresql://primary/db",
            "POSTGRES_URL": "postgresql://secondary/db",
        }
        with patch.dict(os.environ, env, clear=False):
            result = get_url()
            assert result == "postgresql://primary/db"

    @pytest.mark.unit
    def test_builds_url_from_components(self):
        env = {
            "POSTGRES_PASSWORD": "secret",
            "POSTGRES_HOST": "myhost",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "mydb",
            "POSTGRES_USER": "myuser",
        }
        # Remove full URL vars so component building is triggered
        clean_env = {k: v for k, v in os.environ.items()
                     if k not in ("DATABASE_URL", "POSTGRES_URL")}
        clean_env.update(env)
        with patch.dict(os.environ, clean_env, clear=True):
            result = get_url()
            assert "myhost" in result
            assert "5433" in result
            assert "mydb" in result
            assert "myuser" in result
            assert "secret" in result

    @pytest.mark.unit
    def test_uses_default_host_when_not_set(self):
        clean_env = {
            "POSTGRES_PASSWORD": "secret",
        }
        with patch.dict(os.environ, clean_env, clear=True):
            result = get_url()
            assert "localhost" in result

    @pytest.mark.unit
    def test_uses_default_port_when_not_set(self):
        clean_env = {
            "POSTGRES_PASSWORD": "secret",
        }
        with patch.dict(os.environ, clean_env, clear=True):
            result = get_url()
            assert "5432" in result

    @pytest.mark.unit
    def test_uses_default_db_when_not_set(self):
        clean_env = {
            "POSTGRES_PASSWORD": "secret",
        }
        with patch.dict(os.environ, clean_env, clear=True):
            result = get_url()
            assert "n8n" in result

    @pytest.mark.unit
    def test_uses_default_user_when_not_set(self):
        clean_env = {
            "POSTGRES_PASSWORD": "secret",
        }
        with patch.dict(os.environ, clean_env, clear=True):
            result = get_url()
            assert "n8n_user" in result

    @pytest.mark.unit
    def test_raises_runtime_error_when_no_credentials(self):
        """When neither URL nor password is set, RuntimeError must be raised."""
        clean_env = {}  # No credentials at all
        with patch.dict(os.environ, clean_env, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                get_url()
            assert "DATABASE_URL" in str(exc_info.value) or "POSTGRES_PASSWORD" in str(
                exc_info.value
            )

    @pytest.mark.unit
    def test_url_format_is_postgresql_scheme(self):
        clean_env = {
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_HOST": "dbhost",
            "POSTGRES_DB": "testdb",
            "POSTGRES_USER": "testuser",
        }
        with patch.dict(os.environ, clean_env, clear=True):
            result = get_url()
            assert result.startswith("postgresql://")

    @pytest.mark.unit
    def test_url_contains_at_sign(self):
        """URL should follow user:pass@host format."""
        clean_env = {
            "POSTGRES_PASSWORD": "secret",
            "POSTGRES_HOST": "dbhost",
        }
        with patch.dict(os.environ, clean_env, clear=True):
            result = get_url()
            assert "@" in result

    @pytest.mark.unit
    def test_password_included_in_built_url(self):
        my_pass = "super-secret-pass-xyz"
        clean_env = {"POSTGRES_PASSWORD": my_pass}
        with patch.dict(os.environ, clean_env, clear=True):
            result = get_url()
            assert my_pass in result


# =============================================================================
# Initial schema migration metadata
# =============================================================================


def _read_migration_source() -> str:
    """Read the initial schema migration file source."""
    import pathlib

    path = (
        pathlib.Path(__file__).parent.parent.parent
        / "migrations"
        / "versions"
        / "20241204_000000_001_initial_schema.py"
    )
    with open(str(path)) as f:
        return f.read()


def _parse_migration_metadata() -> dict:
    """Extract top-level metadata assignments from the migration file."""
    source = _read_migration_source()
    ns: dict = {}
    safe_lines = [
        line
        for line in source.splitlines()
        if line.startswith("revision")
        or line.startswith("down_revision")
        or line.startswith("branch_labels")
        or line.startswith("depends_on")
    ]
    exec("\n".join(safe_lines), ns)
    return ns


class TestInitialSchemaMigration:
    """Tests for the initial_schema migration script metadata and structure."""

    @pytest.mark.unit
    def test_revision_is_001(self):
        ns = _parse_migration_metadata()
        assert ns.get("revision") == "001"

    @pytest.mark.unit
    def test_down_revision_is_none(self):
        """This is the initial migration so down_revision should be None."""
        ns = _parse_migration_metadata()
        assert ns.get("down_revision") is None

    @pytest.mark.unit
    def test_upgrade_function_exists(self):
        assert "def upgrade" in _read_migration_source()

    @pytest.mark.unit
    def test_downgrade_function_exists(self):
        assert "def downgrade" in _read_migration_source()

    @pytest.mark.unit
    def test_upgrade_creates_judicial_schema(self):
        assert "CREATE SCHEMA IF NOT EXISTS judicial" in _read_migration_source()

    @pytest.mark.unit
    def test_upgrade_creates_audit_schema(self):
        assert "CREATE SCHEMA IF NOT EXISTS audit" in _read_migration_source()

    @pytest.mark.unit
    def test_upgrade_creates_uuid_ossp_extension(self):
        assert "uuid-ossp" in _read_migration_source()

    @pytest.mark.unit
    def test_upgrade_creates_pg_trgm_extension(self):
        assert "pg_trgm" in _read_migration_source()

    @pytest.mark.unit
    def test_downgrade_drops_all_tables(self):
        source = _read_migration_source()
        for table in [
            "cases", "documents", "firac_analyses", "jurisprudence_searches",
            "distinguish_analyses", "generated_documents", "notifications", "logs",
        ]:
            assert table in source, f"Table '{table}' not found in migration source"

    @pytest.mark.unit
    def test_downgrade_drops_schemas(self):
        source = _read_migration_source()
        assert "DROP SCHEMA IF EXISTS audit CASCADE" in source
        assert "DROP SCHEMA IF EXISTS judicial CASCADE" in source

    @pytest.mark.unit
    def test_enum_duplicate_object_exception_handling(self):
        """Enum creation uses DO $$ ... EXCEPTION WHEN duplicate_object pattern."""
        assert "duplicate_object" in _read_migration_source()

    @pytest.mark.unit
    def test_update_trigger_function_defined(self):
        """The update_updated_at_column trigger function should be defined."""
        assert "update_updated_at_column" in _read_migration_source()

    @pytest.mark.unit
    def test_triggers_applied_to_cases(self):
        """UPDATE trigger should be applied to judicial.cases table."""
        source = _read_migration_source()
        assert "update_cases_updated_at" in source

    @pytest.mark.unit
    def test_triggers_applied_to_generated_documents(self):
        """UPDATE trigger should be applied to judicial.generated_documents table."""
        source = _read_migration_source()
        assert "update_generated_documents_updated_at" in source

    @pytest.mark.unit
    def test_downgrade_drops_triggers(self):
        """Downgrade must clean up the triggers and trigger function."""
        source = _read_migration_source()
        assert "DROP TRIGGER IF EXISTS update_cases_updated_at" in source
        assert "DROP FUNCTION IF EXISTS update_updated_at_column" in source