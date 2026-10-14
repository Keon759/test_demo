from copy import deepcopy
import io
import json
import pytest
from backend.app import create_app
from backend.pipeline import run_pipeline
from backend.planner import DEFAULT_PRD, offline_plan, openai_plan, validate_plan


@pytest.fixture()
def prd():
    return DEFAULT_PRD.read_text(encoding="utf-8")


def test_pipeline_finds_injected_defect_and_replays_fixed_mode(prd, tmp_path):
    result = run_pipeline(prd, output_dir=tmp_path / "buggy")
    assert result["summary"] == {"requirements": 10, "total": 13, "passed": 12, "failed": 1, "errors": 0, "bugs": 1}
    bug = result["bugs"][0]
    assert bug["requirement_ids"] == ["REG-002"]
    assert bug["expected_status"] == 400 and bug["actual_status"] == 201
    plan = json.loads((tmp_path / "buggy" / "plan.json").read_text(encoding="utf-8"))
    fixed = run_pipeline(prd, inject_bug=False, plan=plan, output_dir=tmp_path / "fixed")
    assert fixed["summary"] == {**result["summary"], "passed": 13, "failed": 0, "bugs": 0}
    assert fixed["cases"] == result["cases"]
    assert fixed["metadata"]["provider"] == "replay"
    assert len(json.loads((tmp_path / "buggy" / "execution.json").read_text(encoding="utf-8"))) == 13
    assert "| 失败 | 1 |" in (tmp_path / "buggy" / "report.md").read_text(encoding="utf-8")
    assert "REG-002" in (tmp_path / "buggy" / "bugs.md").read_text(encoding="utf-8")


def test_repeat_runs_do_not_reuse_test_data(prd):
    first, second = run_pipeline(prd), run_pipeline(prd)
    assert first["records"] == second["records"]
    assert first["bugs"] == second["bugs"]


def test_offline_cases_follow_changed_prd_boundary(prd):
    changed = prd.replace("大于等于 6 位", "大于等于 8 位")
    cases = {case["id"]: case for case in offline_plan(changed)["cases"]}
    assert len(cases["TC-REG-005"]["payload"]["username"]) == 7
    assert len(cases["TC-REG-007"]["payload"]["username"]) == 8
    assert len(cases["TC-REG-004"]["payload"]["password"]) == 7
    assert len(cases["TC-REG-008"]["payload"]["password"]) == 8
    with pytest.raises(ValueError):
        offline_plan("An unrelated business PRD")


@pytest.mark.parametrize("mutation", ["endpoint", "unknown_requirement", "duplicate_id", "fake_quote", "bad_status", "uncovered"])
def test_reject_invalid_generated_plans(prd, mutation):
    plan = deepcopy(offline_plan(prd))
    if mutation == "endpoint":
        plan["cases"][0]["endpoint"] = "https://untrusted.example"
    elif mutation == "unknown_requirement":
        plan["cases"][0]["requirement_ids"] = ["MISSING"]
    elif mutation == "duplicate_id":
        plan["cases"][1]["id"] = plan["cases"][0]["id"]
    elif mutation == "fake_quote":
        plan["requirements"][0]["source_quote"] = "Invented requirement"
    elif mutation == "bad_status":
        plan["cases"][0]["expected_status"] = True
    else:
        plan["cases"] = plan["cases"][:1]
    with pytest.raises(ValueError):
        validate_plan(plan, prd)


def test_setup_failure_is_execution_error_not_product_bug(prd):
    plan = offline_plan(prd)
    plan["cases"][0]["setup"] = [{"username": "", "password": ""}]
    result = run_pipeline(prd, plan=plan)
    assert result["summary"]["errors"] == 1
    assert result["records"][0]["status"] == "error"
    assert result["records"][0]["actual_status"] is None
    assert result["summary"]["bugs"] == 1


def test_openai_request_schema_and_validated_response(prd, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "unit-test-model")
    expected = offline_plan(prd)
    def transport(request, timeout):
        body = json.loads(request.data)
        assert request.full_url == "https://api.openai.com/v1/responses"
        assert body["store"] is False and body["input"] == prd
        assert body["text"]["format"]["strict"] is True
        assert body["model"] == "unit-test-model"
        assert "known injected bugs" in body["instructions"]
        return io.StringIO(json.dumps({"id": "resp_mock", "model": "unit-test-model",
            "usage": {"input_tokens": 100, "output_tokens": 300}, "status": "completed", "output": [{"type": "message",
            "content": [{"type": "output_text", "text": json.dumps(expected)}]}]}))
    provenance = {}
    assert openai_plan(prd, transport=transport, metadata=provenance) == expected
    assert provenance["response_id"] == "resp_mock"
    assert provenance["usage"]["output_tokens"] == 300
    assert len(provenance["prompt_sha256"]) == 64
    assert "unit-test-placeholder" not in json.dumps(provenance)


@pytest.mark.parametrize("response", [
    {"status": "incomplete", "output": []},
    {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}]},
    {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "invalid"}]}]},
])
def test_model_errors_do_not_silently_fall_back(prd, monkeypatch, response):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "unit-test-model")
    with pytest.raises(ValueError):
        openai_plan(prd, transport=lambda *args, **kwargs: io.StringIO(json.dumps(response)))


def test_openai_mode_requires_explicit_configuration(prd, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    with pytest.raises(ValueError, match="requires"):
        run_pipeline(prd, provider="openai")


@pytest.mark.parametrize("model", ["sk-proj-unit-test-placeholder", "SK-test-placeholder", "same-placeholder", "bad model name"])
def test_reject_key_as_model_before_network_request(prd, monkeypatch, model):
    monkeypatch.setenv("OPENAI_API_KEY", "same-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", model)
    def must_not_call(*args, **kwargs):
        pytest.fail("Invalid model must be rejected before any network request")
    with pytest.raises(ValueError) as captured:
        openai_plan(prd, transport=must_not_call)
    assert model not in str(captured.value)


def test_browser_pipeline_does_not_modify_user_database(tmp_path):
    app = create_app(str(tmp_path / "real.db"))
    with app.test_client() as client:
        credentials = {"username": "tester01", "password": "secret123"}
        assert client.post("/api/register", json=credentials).status_code == 201
        result = client.post("/api/demo/run", json={"inject_bug": True}).get_json()
        assert result["summary"]["failed"] == 1
        fixed = client.post("/api/demo/run", json={"inject_bug": False}).get_json()
        assert fixed["summary"]["failed"] == 0
        assert client.post("/api/login", json=credentials).status_code == 200
        assert client.post("/api/demo/run", json={"inject_bug": "false"}).status_code == 400
