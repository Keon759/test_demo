"""Run one real model request; never load a key from a command-line argument."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.model_validation import validate_model


def main():
    parser = argparse.ArgumentParser(description="One model request, then defect and regression validation")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / ("model-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")))
    args = parser.parse_args()
    try:
        evaluation = validate_model(output_dir=args.output)
    except (ValueError, OSError) as exc:
        print(f"Model validation stopped: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(evaluation, ensure_ascii=False, indent=2))
    print(f"Evidence saved at: {args.output.resolve()}")
    return 0 if evaluation["detected_injected_defect"] and evaluation["fixed_run_all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
