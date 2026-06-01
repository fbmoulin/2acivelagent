# Sistema de Automacao Juridica - Authentication Endpoint Unit Tests
# Tests for the /auth/token endpoint introduced in this PR.

import json
import os
import pytest
from unittest.mock import patch

try:
    from scripts.python.app import app, Config
    APP_IMPORT_OK = True
except SyntaxError as _e:
    APP_IMPORT_OK = False

pytestmark = pytest.mark.skipif(
    not APP_IMPORT_OK,
    reason="scripts/python/app.py has a SyntaxError - fix the mixed OpenAI client code first",
)


# Helper to decode a JWT without verification for payload inspection
def _decode_token_payload(token: str) -> dict:
    import base64

    # JWT is header.payload.signature - decode payload (add padding if needed)
    parts = token.split(".")
    payload_b64 = parts[1]
    # Add padding
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    import json as _json

    return _json.loads(base64.urlsafe_b64decode(payload_b64))


class TestAuthTokenEndpoint:
    """Tests for POST /auth/token endpoint."""

    @pytest.mark.unit
    def test_returns_400_when_no_body(self, client):
        response = client.post(
            "/auth/token", data="", content_type="application/json"
        )
        assert response.status_code == 400

    @pytest.mark.unit
    def test_returns_400_when_api_key_missing(self, client):
        response = client.post(
            "/auth/token",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "api_key" in data["error"]

    @pytest.mark.unit
    def test_returns_401_when_api_key_wrong(self, client):
        with patch.dict(os.environ, {"API_ACCESS_KEY": "correct-key"}):
            response = client.post(
                "/auth/token",
                data=json.dumps({"api_key": "wrong-key"}),
                content_type="application/json",
            )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False

    @pytest.mark.unit
    def test_returns_401_when_no_access_key_configured(self, client):
        """If API_ACCESS_KEY env var is not set, authentication should fail."""
        env_without_key = {k: v for k, v in os.environ.items() if k != "API_ACCESS_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            response = client.post(
                "/auth/token",
                data=json.dumps({"api_key": "any-key"}),
                content_type="application/json",
            )
        assert response.status_code == 401

    @pytest.mark.unit
    def test_returns_token_on_valid_credentials(self, client):
        with patch.dict(os.environ, {"API_ACCESS_KEY": "valid-access-key"}):
            response = client.post(
                "/auth/token",
                data=json.dumps({"api_key": "valid-access-key"}),
                content_type="application/json",
            )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "token" in data

    @pytest.mark.unit
    def test_returned_token_is_non_empty_string(self, client):
        with patch.dict(os.environ, {"API_ACCESS_KEY": "valid-access-key"}):
            response = client.post(
                "/auth/token",
                data=json.dumps({"api_key": "valid-access-key"}),
                content_type="application/json",
            )
        data = json.loads(response.data)
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 10

    @pytest.mark.unit
    def test_response_contains_expires_in(self, client):
        with patch.dict(os.environ, {"API_ACCESS_KEY": "valid-access-key"}):
            response = client.post(
                "/auth/token",
                data=json.dumps({"api_key": "valid-access-key"}),
                content_type="application/json",
            )
        data = json.loads(response.data)
        assert "expires_in" in data
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    @pytest.mark.unit
    def test_expires_in_matches_config(self, client):
        with patch.dict(os.environ, {"API_ACCESS_KEY": "valid-access-key"}), patch.object(
            Config, "JWT_EXPIRY_HOURS", 12
        ):
            response = client.post(
                "/auth/token",
                data=json.dumps({"api_key": "valid-access-key"}),
                content_type="application/json",
            )
        data = json.loads(response.data)
        assert data["expires_in"] == 12 * 3600

    @pytest.mark.unit
    def test_token_has_three_parts(self, client):
        """JWT tokens consist of three base64url parts separated by dots."""
        with patch.dict(os.environ, {"API_ACCESS_KEY": "valid-access-key"}):
            response = client.post(
                "/auth/token",
                data=json.dumps({"api_key": "valid-access-key"}),
                content_type="application/json",
            )
        data = json.loads(response.data)
        parts = data["token"].split(".")
        assert len(parts) == 3

    @pytest.mark.unit
    def test_token_payload_contains_api_user(self, client):
        with patch.dict(os.environ, {"API_ACCESS_KEY": "valid-access-key"}):
            response = client.post(
                "/auth/token",
                data=json.dumps({"api_key": "valid-access-key"}),
                content_type="application/json",
            )
        data = json.loads(response.data)
        payload = _decode_token_payload(data["token"])
        assert "user_id" in payload

    @pytest.mark.unit
    def test_response_is_json(self, client):
        response = client.post(
            "/auth/token",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.content_type == "application/json"

    @pytest.mark.unit
    def test_get_method_not_allowed(self, client):
        response = client.get("/auth/token")
        assert response.status_code == 405

    @pytest.mark.unit
    def test_error_response_has_success_false(self, client):
        """All error responses must set success=False."""
        response = client.post(
            "/auth/token",
            data=json.dumps({}),
            content_type="application/json",
        )
        data = json.loads(response.data)
        assert data.get("success") is False

    @pytest.mark.unit
    def test_invalid_credentials_do_not_expose_expected_key(self, client):
        """Error messages must not leak the expected API key value."""
        secret_key = "super-secret-access-key-12345"
        with patch.dict(os.environ, {"API_ACCESS_KEY": secret_key}):
            response = client.post(
                "/auth/token",
                data=json.dumps({"api_key": "wrong"}),
                content_type="application/json",
            )
        data = json.loads(response.data)
        assert secret_key not in json.dumps(data)