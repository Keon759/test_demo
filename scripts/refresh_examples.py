"""Regenerate public offline evidence and matching human-readable docs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.pipeline import run_pipeline


def main():
    buggy_dir, fixed_dir = ROOT / "examples/offline-buggy", ROOT / "examples/offline-fixed"
    buggy = run_pipeline(output_dir=buggy_dir)
    plan = {"requirements": buggy["requirements"], "cases": buggy["cases"]}
    fixed = run_pipeline(plan=plan, inject_bug=False, output_dir=fixed_dir)
    docs = ROOT / "docs"
    cases = ["# 可执行测试用例", "", "2026-10-13 后续完善的离线规则模式；以下表格由实际运行计划生成。", "",
             "每条用例使用独立数据库。完整数据与前置注册见 [测试计划](../examples/offline-buggy/plan.json)。", "",
             "| 用例 | 场景 | 关联需求 | 接口 | 预期状态码 |", "| --- | --- | --- | --- | --- |"]
    for case in buggy["cases"]:
        cases.append(f"| {case['id']} | {case['title']} | {', '.join(case['requirement_ids'])} | {case['endpoint']} | {case['expected_status']} |")
    (docs / "03-测试用例.md").write_text("\n".join(cases) + "\n", encoding="utf-8")
    records = ["# 实际接口执行记录", "", "本页为后续完善版本的本次运行结果，不作为原始实习期间的执行证明。", "",
               f"生成时间（UTC）：{buggy['metadata']['generated_at']}", "",
               "执行方式：Flask test client；本页不合并手工记录与接口记录，避免重复计数。", "",
               "| 用例 | 预期 | 实际 | 结果 |", "| --- | --- | --- | --- |"]
    for record in buggy["records"]:
        records.append(f"| {record['case_id']} | {record['expected_status']} | {record['actual_status']} | {record['status']} |")
    records += ["", "原始响应见 [execution.json](../examples/offline-buggy/execution.json)。",
                "同一计划修复回放见 [修复报告](../examples/offline-fixed/report.md)。"]
    (docs / "04-执行记录.md").write_text("\n".join(records) + "\n", encoding="utf-8")
    (docs / "05-测试报告.md").write_text(buggy["documents"]["report.md"], encoding="utf-8")
    (docs / "06-Bug单.md").write_text(buggy["documents"]["bugs.md"], encoding="utf-8")
    print(json.dumps({"buggy": buggy["summary"], "fixed": fixed["summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
