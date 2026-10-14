"""Generate executable plans without executing model-written code."""

import json
import hashlib
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRD = ROOT / "docs" / "01-PRD.md"
PROMPT = ROOT / "prompts" / "generate-plan.txt"


def object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


PAYLOAD_SCHEMA = object_schema({"username": {"type": "string"}, "password": {"type": "string"}})
PLAN_SCHEMA = object_schema({
    "requirements": {"type": "array", "items": object_schema({
        "id": {"type": "string"}, "module": {"type": "string", "enum": ["注册", "登录"]},
        "description": {"type": "string"}, "source_quote": {"type": "string"}})},
    "cases": {"type": "array", "items": object_schema({
        "id": {"type": "string"}, "title": {"type": "string"},
        "requirement_ids": {"type": "array", "items": {"type": "string"}},
        "endpoint": {"type": "string", "enum": ["/api/register", "/api/login"]},
        "setup": {"type": "array", "items": PAYLOAD_SCHEMA},
        "payload": PAYLOAD_SCHEMA,
        "expected_status": {"type": "integer", "enum": [200, 201, 400, 401, 409]}})}
})


def _check_schema(value, schema, path="plan"):
    """Validate the small, explicit JSON Schema subset used by this contract."""
    kind = schema["type"]
    valid = {"object": isinstance(value, dict), "array": isinstance(value, list),
             "string": isinstance(value, str), "integer": type(value) is int}[kind]
    if not valid:
        raise ValueError(f"{path}: expected {kind}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: unsupported value")
    if kind == "object":
        if set(value) != set(schema["required"]):
            raise ValueError(f"{path}: missing or unexpected fields")
        for key, child in schema["properties"].items():
            _check_schema(value[key], child, f"{path}.{key}")
    elif kind == "array":
        for index, child in enumerate(value):
            _check_schema(child, schema["items"], f"{path}[{index}]")


def validate_plan(plan, prd):
    _check_schema(plan, PLAN_SCHEMA)
    if not 1 <= len(plan["requirements"]) <= 40 or not 1 <= len(plan["cases"]) <= 40:
        raise ValueError("A plan needs 1-40 requirements and 1-40 cases")
    requirement_ids = [item["id"] for item in plan["requirements"]]
    case_ids = [item["id"] for item in plan["cases"]]
    for identifiers in (requirement_ids, case_ids):
        if len(set(identifiers)) != len(identifiers) or any(
            not re.fullmatch(r"[A-Z][A-Z0-9-]{0,39}", item) for item in identifiers
        ):
            raise ValueError("IDs must be unique, short uppercase identifiers")
    for requirement in plan["requirements"]:
        if not requirement["source_quote"].strip() or requirement["source_quote"] not in prd:
            raise ValueError("Requirement source_quote must appear verbatim in the PRD")
        if not requirement["description"].strip():
            raise ValueError("Requirement descriptions cannot be empty")
    covered = set()
    for case in plan["cases"]:
        references = case["requirement_ids"]
        if not references or not set(references).issubset(requirement_ids):
            raise ValueError("Every case must reference existing requirements")
        if not case["title"].strip() or len(case["setup"]) > 2:
            raise ValueError("Cases need a title and at most two setup registrations")
        for payload in [case["payload"], *case["setup"]]:
            if any(len(value) > 128 for value in payload.values()):
                raise ValueError("Test credentials are limited to 128 characters")
        covered.update(references)
    if covered != set(requirement_ids):
        raise ValueError("Every extracted requirement must have a test case")
    return plan


def offline_plan(prd):
    """A limited rule parser for this auth PRD, explicitly not an LLM."""
    section = re.search(r"## 3\. 功能需求(.*?)## 4\.", prd, re.S)
    if not section:
        raise ValueError("Offline mode supports the supplied auth PRD section format only")
    features = section.group(1)
    username_match = re.search(r"用户名长度必须大于等于\s*(\d+)\s*位", features)
    password_match = re.search(r"密码长度必须大于等于\s*(\d+)\s*位", features)
    if not username_match or not password_match:
        raise ValueError("Offline mode needs explicit username/password minimum lengths")
    username_min, password_min = int(username_match[1]), int(password_match[1])
    if not 2 <= username_min <= 64 or not 2 <= password_min <= 64:
        raise ValueError("Offline minimum lengths must be between 2 and 64")
    specs = [
        ("REG-001", "注册", "用户名不能为空。"),
        ("REG-002", "注册", username_match[0] + "。"),
        ("REG-003", "注册", "用户名不可重复。"),
        ("REG-004", "注册", "密码不能为空。"),
        ("REG-005", "注册", password_match[0] + "。"),
        ("REG-006", "注册", "注册成功后返回成功提示。"),
        ("LOG-001", "登录", "用户名不能为空。"),
        ("LOG-002", "登录", "密码不能为空。"),
        ("LOG-003", "登录", "用户名或密码错误时返回错误提示。"),
        ("LOG-004", "登录", "登录成功后进入登录成功页面。"),
    ]
    register, login = features.split("### 3.2 用户登录", 1)
    for _, module, quote in specs:
        if quote not in (register if module == "注册" else login):
            raise ValueError("Offline mode does not recognize this PRD; use the supplied example")
    requirements = [{"id": rid, "module": module, "description": quote.rstrip("。"),
                     "source_quote": quote} for rid, module, quote in specs]
    user, password = "u" * max(8, username_min), "p" * max(9, password_min)
    normal = {"username": user, "password": password}
    cases = []

    def add(cid, title, rid, endpoint, payload, expected, setup=None):
        cases.append({"id": cid, "title": title, "requirement_ids": [rid],
                      "endpoint": "/api/" + endpoint, "setup": setup or [],
                      "payload": payload, "expected_status": expected})

    add("TC-REG-001", "合法用户注册成功", "REG-006", "register", normal, 201)
    add("TC-REG-002", "空用户名不可注册", "REG-001", "register", {**normal, "username": ""}, 400)
    add("TC-REG-003", "空密码不可注册", "REG-004", "register", {**normal, "password": ""}, 400)
    add("TC-REG-004", "密码低于最小长度", "REG-005", "register", {**normal, "password": "p" * (password_min - 1)}, 400)
    add("TC-REG-005", "用户名低于最小长度", "REG-002", "register", {**normal, "username": "u" * (username_min - 1)}, 400)
    add("TC-REG-006", "重复用户名不可注册", "REG-003", "register", normal, 409, [normal])
    add("TC-REG-007", "用户名恰好达到最小长度", "REG-002", "register", {**normal, "username": "u" * username_min}, 201)
    add("TC-REG-008", "密码恰好达到最小长度", "REG-005", "register", {**normal, "password": "p" * password_min}, 201)
    add("TC-LOG-001", "合法用户登录成功", "LOG-004", "login", normal, 200, [normal])
    add("TC-LOG-002", "错误密码不可登录", "LOG-003", "login", {**normal, "password": "wrong-password"}, 401, [normal])
    add("TC-LOG-003", "未注册用户不可登录", "LOG-003", "login", normal, 401)
    add("TC-LOG-004", "空用户名不可登录", "LOG-001", "login", {**normal, "username": ""}, 400)
    add("TC-LOG-005", "空密码不可登录", "LOG-002", "login", {**normal, "password": ""}, 400)
    return validate_plan({"requirements": requirements, "cases": cases}, prd)


def openai_plan(prd, *, transport=None, metadata=None):
    """One explicit Responses API request; no silent fallback to offline mode."""
    key, model = os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_MODEL")
    if not key or not model:
        raise ValueError("OpenAI mode requires OPENAI_API_KEY and OPENAI_MODEL environment variables")
    request_body = {"model": model, "store": False,
                    "instructions": PROMPT.read_text(encoding="utf-8"), "input": prd,
                    "max_output_tokens": 10000,
                    "text": {"format": {"type": "json_schema", "name": "auth_test_plan",
                                        "strict": True, "schema": PLAN_SCHEMA}}}
    request = Request("https://api.openai.com/v1/responses",
                      data=json.dumps(request_body).encode("utf-8"),
                      headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with (transport or urlopen)(request, timeout=90) as response:
            headers = getattr(response, "headers", {})
            request_id = headers.get("x-request-id")
            result = json.load(response)
    except HTTPError as exc:
        raise ValueError(f"OpenAI request failed (HTTP {exc.code}); check account/model access") from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise ValueError("OpenAI request failed or returned invalid JSON; no offline fallback was used") from None
    if not isinstance(result, dict) or result.get("status") != "completed":
        raise ValueError("OpenAI response was incomplete; no tests were executed")
    fragments = []
    for item in result.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "refusal":
                raise ValueError("Model refused the request; no tests were executed")
            if content.get("type") == "output_text":
                fragments.append(content.get("text", ""))
    try:
        plan = json.loads("".join(fragments))
    except json.JSONDecodeError:
        raise ValueError("Model did not return a JSON test plan") from None
    plan = validate_plan(plan, prd)
    if metadata is not None:
        # Preserve only diagnostic identifiers and usage; never credentials or headers.
        metadata.update({"provider": "openai", "requested_model": model,
                         "returned_model": result.get("model"), "response_id": result.get("id"),
                         "request_id": request_id, "usage": result.get("usage"),
                         "prompt_sha256": hashlib.sha256(request_body["instructions"].encode()).hexdigest()})
    return plan
