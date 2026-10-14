"""One model request followed by defect detection and same-plan regression."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from backend.pipeline import run_pipeline
from backend.planner import DEFAULT_PRD, openai_plan


def evaluate_runs(buggy, fixed):
    fixed_records = {item["case_id"]: item for item in fixed["records"]}
    reproduced = []
    for item in buggy["records"]:
        payload = item["payload"]
        counterpart = fixed_records[item["case_id"]]
        if (item["endpoint"] == "/api/register" and 0 < len(payload["username"].strip()) < 6
                and len(payload["password"]) >= 6 and item["expected_status"] == 400
                and item["actual_status"] == 201 and item["status"] == "failed"
                and counterpart["actual_status"] == 400 and counterpart["status"] == "passed"):
            reproduced.append(item["case_id"])
    return {"case_count": buggy["summary"]["total"], "detected_injected_defect": bool(reproduced),
            "defect_case_ids": reproduced, "same_plan_replayed": buggy["cases"] == fixed["cases"],
            "fixed_run_all_passed": fixed["summary"]["passed"] == fixed["summary"]["total"]
                and fixed["summary"]["errors"] == 0,
            "buggy_summary": buggy["summary"], "fixed_summary": fixed["summary"]}


def validate_model(*, output_dir, prd=None):
    prd = DEFAULT_PRD.read_text(encoding="utf-8") if prd is None else prd
    if not isinstance(prd, str) or not prd.strip() or len(prd) > 32000:
        raise ValueError("PRD must be nonempty text of at most 32000 characters")
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory is not empty; choose a new directory to preserve earlier evidence")
    # One paid model call. Both runs then use exactly this validated plan.
    provenance = {}
    plan = openai_plan(prd, metadata=provenance)
    output.mkdir(parents=True, exist_ok=True)
    provenance.update({"generated_at": datetime.now(timezone.utc).isoformat(),
                       "prd_sha256": hashlib.sha256(prd.encode()).hexdigest(),
                       "plan_sha256": hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()).hexdigest()})
    (output / "model-call.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    buggy = run_pipeline(prd, plan=plan, output_dir=output / "buggy")
    fixed = run_pipeline(prd, plan=plan, inject_bug=False, output_dir=output / "fixed")
    evaluation = evaluate_runs(buggy, fixed)
    evaluation["scope"] = "One auth PRD, API status-code checks; not a general model accuracy benchmark"
    evaluation["requires_human_semantic_review"] = True
    (output / "evaluation.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = ["# 单次真实模型验证", "",
              f"生成时间（UTC）：{provenance['generated_at']}",
              f"调用记录：见 model-call.json；实际返回模型：{provenance.get('returned_model')}", "",
              "模型只生成一份计划，两次运行均回放该计划。程序不会自动重试付费请求，也不会自动上传文件。", "",
              "| 观测项 | 实际结果 |", "| --- | --- |",
              f"| 生成用例数 | {evaluation['case_count']} |",
              f"| 检出用户名长度缺陷 | {evaluation['detected_injected_defect']} |",
              f"| 检出并在修复后通过的用例 | {', '.join(evaluation['defect_case_ids']) or '无'} |",
              f"| 同一计划回放 | {evaluation['same_plan_replayed']} |",
              f"| 修复模式全部通过 | {evaluation['fixed_run_all_passed']} |", "",
              "原始响应与逐条统计分别见 buggy/ 和 fixed/。这是一个 PRD 的验证，不是通用准确率证明。",
              "仍需人工检查需求遗漏、用例预期、引用是否正确；未检测出缺陷或回归仍失败时，不应宣称验证完成。"]
    (output / "evaluation.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return evaluation
