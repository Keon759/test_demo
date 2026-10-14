"""Run from the repository root: python -m backend.run_pipeline."""
import argparse
import json
from pathlib import Path
import sys

from backend.pipeline import run_pipeline
from backend.planner import DEFAULT_PRD


def main():
    parser = argparse.ArgumentParser(description="Generate a plan, execute isolated API cases and write reports")
    parser.add_argument("--prd", type=Path, default=DEFAULT_PRD)
    parser.add_argument("--provider", choices=["offline", "openai"], default="offline")
    parser.add_argument("--fixed", action="store_true", help="Disable the injected username bug")
    parser.add_argument("--output", type=Path, default=Path("artifacts/latest"))
    parser.add_argument("--plan", type=Path, help="Replay a saved plan (no model API call)")
    parser.add_argument("--fail-on-defect", action="store_true", help="Return exit 1 for failed business cases")
    args = parser.parse_args()
    try:
        prd = args.prd.read_text(encoding="utf-8")
        plan = json.loads(args.plan.read_text(encoding="utf-8")) if args.plan else None
        result = run_pipeline(prd, provider=args.provider, inject_bug=not args.fixed, output_dir=args.output, plan=plan)
    except (ValueError, OSError) as exc:
        print(f"Pipeline stopped: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"provider": result["metadata"]["provider"], **result["summary"]}, ensure_ascii=False))
    print(f"Artifacts: {args.output.resolve()}")
    return int(bool(result["summary"]["errors"] or (args.fail_on_defect and result["summary"]["failed"])))


if __name__ == "__main__":
    raise SystemExit(main())
