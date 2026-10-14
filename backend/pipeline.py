"""Plan -> isolated API execution -> traceable reports and local bug tickets."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

from backend.planner import DEFAULT_PRD, offline_plan, openai_plan, validate_plan


def execute_plan(plan, *, inject_bug=True):
    from backend.app import create_app
    records = []
    with tempfile.TemporaryDirectory(prefix="auth-pipeline-") as directory:
        for index, case in enumerate(plan["cases"]):
            app = create_app(str(Path(directory) / f"case-{index}.db"),
                             inject_bug=inject_bug, enable_demo=False)
            app.config["TESTING"] = True
            record = {"case_id": case["id"], "title": case["title"],
                      "requirement_ids": case["requirement_ids"], "endpoint": case["endpoint"],
                      "payload": case["payload"], "expected_status": case["expected_status"],
                      "setup_results": [], "actual_status": None, "actual_body": None, "status": "error"}
            with app.test_client() as client:
                for payload in case["setup"]:
                    response = client.post("/api/register", json=payload)
                    record["setup_results"].append({"status_code": response.status_code, "body": response.get_json()})
                    if response.status_code != 201:
                        record["error"] = "Setup registration failed; test was not executed"
                        break
                else:
                    response = client.post(case["endpoint"], json=case["payload"])
                    record["actual_status"] = response.status_code
                    record["actual_body"] = response.get_json()
                    record["status"] = "passed" if response.status_code == case["expected_status"] else "failed"
            records.append(record)
    return records


def make_bugs(plan, records):
    requirements = {item["id"]: item for item in plan["requirements"]}
    cases = {item["id"]: item for item in plan["cases"]}
    bugs = {}
    for record in records:
        if record["status"] != "failed":
            continue
        fingerprint = json.dumps([sorted(record["requirement_ids"]), record["endpoint"],
                                  record["expected_status"], record["actual_status"]])
        key = hashlib.sha256(fingerprint.encode()).hexdigest()[:10].upper()
        if key not in bugs:
            bugs[key] = {"id": "BUG-" + key, "title": record["title"] + "：实际结果不符合预期",
                         "state": "open", "delivery": "local_artifact_only",
                         "requirement_ids": record["requirement_ids"], "case_ids": [],
                         "source_quotes": [requirements[rid]["source_quote"] for rid in record["requirement_ids"]],
                         "endpoint": record["endpoint"], "setup": cases[record["case_id"]]["setup"],
                         "payload": record["payload"], "expected_status": record["expected_status"],
                         "actual_status": record["actual_status"], "actual_body": record["actual_body"]}
        bugs[key]["case_ids"].append(record["case_id"])
    return list(bugs.values())


def _cell(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;").replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("`", "\\`")


def render_documents(result):
    summary, metadata = result["summary"], result["metadata"]
    label = {"offline": "离线规则模式（未调用大模型）", "openai": "OpenAI API 模式",
             "replay": "已保存计划回放模式"}[metadata["provider"]]
    report = ["# 自动生成测试报告", "", f"- 生成时间（UTC）：{metadata['generated_at']}",
              f"- 计划来源：{label}", f"- 预埋用户名缺陷：{metadata['inject_bug']}",
              f"- PRD SHA-256：`{metadata['prd_sha256']}`", "",
              "执行方式：Flask test client 调用真实接口处理函数；每条用例独立 SQLite 数据库。",
              "覆盖范围：注册/登录接口状态码与业务规则；不包含浏览器 E2E、性能或安全认证。", "",
              "| 指标 | 数量 |", "| --- | --- |",
              f"| 需求数 | {summary['requirements']} |", f"| 设计用例数 | {summary['total']} |",
              f"| 已执行用例数 | {summary['passed'] + summary['failed']} |",
              f"| 通过 | {summary['passed']} |", f"| 失败 | {summary['failed']} |",
              f"| 执行错误/前置失败 | {summary['errors']} |", f"| 去重缺陷单 | {summary['bugs']} |", "",
              "| 用例 | 关联需求 | 预期状态码 | 实际状态码 | 结果 |", "| --- | --- | --- | --- | --- |"]
    for item in result["records"]:
        report.append(f"| {item['case_id']} | {', '.join(item['requirement_ids'])} | {item['expected_status']} | {item['actual_status']} | {item['status']} |")
    report += ["", "所有统计直接来自 execution.json；预埋缺陷造成的用例失败是有效测试结果。",
               "模型模式只负责生成计划，执行与统计由程序完成；模型生成的预期仍需人工审查。"]
    tickets = ["# 自动生成的本地缺陷单", "", "交付方式：生成文件；未向 GitHub Issues、Jira 或其他平台提交。", ""]
    if not result["bugs"]:
        tickets.append("本次执行未产生失败用例，因此没有生成缺陷单。")
    for bug in result["bugs"]:
        tickets += [f"## {bug['id']}：{_cell(bug['title'])}", "",
                    f"- 状态：{bug['state']}", f"- 关联需求：{', '.join(bug['requirement_ids'])}",
                    f"- 关联用例：{', '.join(bug['case_ids'])}", f"- PRD 原文：{_cell('; '.join(bug['source_quotes']))}",
                    f"- 前置注册：`{_cell(json.dumps(bug['setup'], ensure_ascii=False))}`",
                    f"- 请求：POST `{bug['endpoint']}`，`{_cell(json.dumps(bug['payload'], ensure_ascii=False))}`",
                    f"- 预期状态码：{bug['expected_status']}", f"- 实际状态码：{bug['actual_status']}",
                    f"- 实际响应：`{_cell(json.dumps(bug['actual_body'], ensure_ascii=False))}`", ""]
    return {"report.md": "\n".join(report).rstrip() + "\n", "bugs.md": "\n".join(tickets).rstrip() + "\n"}


def run_pipeline(prd=None, *, provider="offline", inject_bug=True, output_dir=None, plan=None):
    if type(inject_bug) is not bool:
        raise ValueError("inject_bug must be a boolean")
    if provider not in {"offline", "openai"}:
        raise ValueError("Unsupported plan provider")
    prd = DEFAULT_PRD.read_text(encoding="utf-8") if prd is None else prd
    if not isinstance(prd, str) or not prd.strip() or len(prd) > 32000:
        raise ValueError("PRD must be nonempty text of at most 32000 characters")
    if plan is not None:
        plan = validate_plan(plan, prd)
        plan_provider = "replay"
    else:
        plan = offline_plan(prd) if provider == "offline" else openai_plan(prd)
        plan_provider = provider
    records = execute_plan(plan, inject_bug=inject_bug)
    bugs = make_bugs(plan, records)
    summary = {"requirements": len(plan["requirements"]), "total": len(records),
               "passed": sum(item["status"] == "passed" for item in records),
               "failed": sum(item["status"] == "failed" for item in records),
               "errors": sum(item["status"] == "error" for item in records), "bugs": len(bugs)}
    result = {"metadata": {"generated_at": datetime.now(timezone.utc).isoformat(),
                           "provider": plan_provider, "model": os.environ.get("OPENAI_MODEL") if plan_provider == "openai" else None,
                           "inject_bug": inject_bug, "prd_sha256": hashlib.sha256(prd.encode()).hexdigest(),
                           "execution": "flask_test_client", "bug_delivery": "local_artifact_only"},
              "requirements": plan["requirements"], "cases": plan["cases"],
              "records": records, "bugs": bugs, "summary": summary}
    result["documents"] = render_documents(result)
    if output_dir is not None:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        assets = {"requirements.json": result["requirements"], "test-cases.json": result["cases"],
                  "execution.json": records, "bugs.json": bugs, "run.json": {"metadata": result["metadata"], "summary": summary}, "plan.json": plan}
        for filename, asset in assets.items():
            (output / filename).write_text(json.dumps(asset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "prd.md").write_text(prd, encoding="utf-8")
        for filename, content in result["documents"].items():
            (output / filename).write_text(content, encoding="utf-8")
    return result
