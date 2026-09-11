"""Regrade an existing paid commitment-v2 result for the assignment PoC.

This command makes no model calls and never alters the original result.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from evals.commitment_v2_holdout_validation import assignment_acceptance


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "result", type=pathlib.Path,
        help="existing commitment-v2 holdout result JSON",
    )
    parser.add_argument("--out", type=pathlib.Path, default=None)
    args = parser.parse_args(argv[1:])

    payload = json.loads(args.result.read_text(encoding="utf-8"))
    report = {
        "source_result": args.result.as_posix(),
        "source_status": payload.get("status"),
        "strict_preregistered_acceptance": payload.get("acceptance"),
        "assignment_acceptance": assignment_acceptance(payload),
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
        print(f"written to {args.out}")
    print(rendered, end="")
    return 0 if report["assignment_acceptance"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
