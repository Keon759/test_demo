import io
import json
from urllib.error import HTTPError
import pytest
from backend.planner import DEFAULT_PRD, describe_api_error, openai_plan


@pytest.mark.parametrize("code, expected", [
    ("insufficient_quota", "Billing and Limits"),
    ("credit_balance_exhausted", "prepaid credits are exhausted"),
    ("project_spend_limit_exceeded", "check Limits"),
    ("organization_spend_limit_exceeded", "check Limits"),
    ("organization_usage_limit_exceeded", "check Limits"),
    ("rate_limit_exceeded", "Wait at least 20 seconds"),
    ("slow_down", "Wait at least 20 seconds"),
])
def test_api_errors_distinguish_billing_and_rate_limits(code, expected):
    body = json.dumps({"error": {"code": code, "type": "insufficient_quota", "message": "private diagnostic text"}}).encode()
    exc = HTTPError("https://api.openai.com/v1/responses", 429, "error", {"Retry-After": "20"}, io.BytesIO(body))
    description = describe_api_error(exc)
    assert code in description
    assert expected in description
    assert "private diagnostic text" not in description


@pytest.mark.parametrize("body", [b"not JSON", b"[]", b'{"error": null}',
    b'{"error": {"code": "sk-unit-test-placeholder", "type": "unexpected-private-text", "message": "private-message"}}'])
def test_unknown_or_malformed_api_errors_do_not_echo_raw_content(body):
    exc = HTTPError("https://api.openai.com/v1/responses", 429, "error", {}, io.BytesIO(body))
    description = describe_api_error(exc)
    assert "code unknown" in description
    assert "sk-unit-test-placeholder" not in description
    assert "private" not in description


def test_rate_limit_type_fallback_and_untrusted_retry_header():
    body = b'{"error": {"code": null, "type": "rate_limit_error"}}'
    exc = HTTPError("https://api.openai.com/v1/responses", 429, "error", {"Retry-After": "private-header"}, io.BytesIO(body))
    description = describe_api_error(exc)
    assert "code rate_limit_error" in description
    assert "No automatic retry" in description
    assert "private-header" not in description


def test_model_request_reports_quota_failure_without_retry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "unit-test-model")
    calls = []
    def transport(*args, **kwargs):
        calls.append(True)
        body = b'{"error": {"code": "insufficient_quota", "message": "unit-test-placeholder"}}'
        raise HTTPError("https://api.openai.com/v1/responses", 429, "error", {}, io.BytesIO(body))
    with pytest.raises(ValueError, match="insufficient_quota") as captured:
        openai_plan(DEFAULT_PRD.read_text(encoding="utf-8"), transport=transport)
    assert len(calls) == 1
    assert "unit-test-placeholder" not in str(captured.value)
