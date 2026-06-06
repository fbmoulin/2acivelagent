# Sistema de Automacao Juridica - App.py Syntax / Import Tests
# These tests verify that scripts/python/app.py can be imported successfully.
# A failure here means there is a syntax or import-time error in the application
# code that must be fixed before other tests can run.

import sys
import importlib
import pytest


class TestAppImportable:
    """Tests that verify scripts/python/app.py is importable without errors."""

    @pytest.mark.unit
    def test_app_module_has_no_syntax_errors(self):
        """
        scripts/python/app.py must not contain SyntaxErrors.

        The PR introduced mixed old/new OpenAI client code in several
        service methods (FIRACAnalyzer, DistinguishAnalyzer, DocumentGenerator).
        Each method has:
            response = openai.ChatCompletion.create(   # old API - line N
            from openai import OpenAI                  # SyntaxError - line N+1
        This needs to be resolved to a single consistent API call pattern.
        """
        try:
            import py_compile
            import pathlib

            app_path = str(
                pathlib.Path(__file__).parent.parent.parent
                / "scripts"
                / "python"
                / "app.py"
            )
            py_compile.compile(app_path, doraise=True)
            syntax_ok = True
            error_msg = ""
        except py_compile.PyCompileError as e:
            syntax_ok = False
            error_msg = str(e)

        assert syntax_ok, (
            f"scripts/python/app.py contains a syntax error: {error_msg}\n"
            "Fix: Remove the duplicate/conflicting OpenAI API calls in "
            "FIRACAnalyzer.analyze(), DistinguishAnalyzer.analyze(), and "
            "DocumentGenerator.generate(). Keep only the new-style client:\n"
            "    from openai import OpenAI\n"
            "    client = OpenAI()\n"
            "    response = client.chat.completions.create(...)"
        )

    @pytest.mark.unit
    def test_app_module_importable(self):
        """scripts/python/app.py must be importable (no import-time errors)."""
        try:
            # Remove cached module to force fresh import
            mods_to_remove = [k for k in sys.modules if "scripts.python.app" in k]
            for mod in mods_to_remove:
                del sys.modules[mod]

            spec = importlib.util.find_spec("scripts.python.app")
            # If find_spec raises (syntax error), this test will fail with the reason
            importable = spec is not None
        except Exception as e:
            importable = False
            pytest.fail(
                f"scripts/python/app.py cannot be located or imported: {e}"
            )

        assert importable, "scripts/python/app.py module cannot be found"

    @pytest.mark.unit
    def test_app_exports_required_symbols(self):
        """
        Once importable, app.py must export the documented public API:
        Config, InputValidator, PDFExtractor, FIRACAnalyzer, DatajudClient,
        DistinguishAnalyzer, DocumentGenerator, app (Flask instance).
        """
        try:
            import scripts.python.app as app_module
            required = [
                "Config",
                "InputValidator",
                "PDFExtractor",
                "FIRACAnalyzer",
                "DatajudClient",
                "DistinguishAnalyzer",
                "DocumentGenerator",
                "app",
                "create_jwt_token",
                "verify_jwt_token",
                "generate_request_id",
                "sanitize_error_message",
                "require_auth",
            ]
            missing = [sym for sym in required if not hasattr(app_module, sym)]
            assert missing == [], f"Missing symbols in app.py: {missing}"
        except SyntaxError as e:
            pytest.fail(
                f"Cannot import scripts/python/app.py due to SyntaxError: {e}\n"
                "Fix the mixed OpenAI API calls before running these tests."
            )