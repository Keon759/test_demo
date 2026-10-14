import json
import pytest

from backend.model_validation import validate_model
from backend.planner import DEFAULT_PRD, offline_plan


def test_model_validation_uses_one_call_and_preserves_evidence(tmp_path, monkeypatch):
    calls = []
    def fake_plan(prd, *, metadata):
        calls.append(prd)
        metadata.update({"provider": "mock", "returned_model": "unit-test-model", "response_id": "resp_mock"})
        return offline_plan(prd)
    monkeypatch.setattr("backend.model_validation.openai_plan", fake_plan)
    output = tmp_path / "run"
    evaluation = validate_model(output_dir=output)
    assert len(calls) == 1
    assert evaluation["detected_injected_defect"] is True
    assert evaluation["fixed_run_all_passed"] is True
    assert evaluation["same_plan_replayed"] is True
    provenance = json.loads((output / "model-call.json").read_text(encoding="utf-8"))
    assert provenance["response_id"] == "resp_mock"
    assert len(provenance["plan_sha256"]) == 64
    assert json.loads((output / "buggy/plan.json").read_text(encoding="utf-8")) == json.loads((output / "fixed/plan.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="not empty"):
        validate_model(output_dir=output)
    assert len(calls) == 1


def test_green_regression_does_not_hide_missing_defect_case(tmp_path, monkeypatch):
    def fake_plan(prd, *, metadata):
        plan = offline_plan(prd)
        plan["cases"] = [item for item in plan["cases"] if item["id"] != "TC-REG-005"]
        return plan
    monkeypatch.setattr("backend.model_validation.openai_plan", fake_plan)
    evaluation = validate_model(output_dir=tmp_path / "missed")
    assert evaluation["fixed_run_all_passed"] is True
    assert evaluation["detected_injected_defect"] is False
    assert evaluation["defect_case_ids"] == []
