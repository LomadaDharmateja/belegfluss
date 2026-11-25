"""Command line: `python -m belegfluss_eval <command>` (run in `eval/`)."""

import argparse
import sys
from pathlib import Path

from belegfluss_eval import gate

ROOT = Path(__file__).resolve().parents[2]  # eval/


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="belegfluss_eval")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("gate", help="replay the baseline with the current code (CI)")
    baseline = commands.add_parser("baseline", help="make a run the new baseline")
    baseline.add_argument("run", help="folder name in recordings/")
    args = parser.parse_args(argv)

    if args.command == "gate":
        problems = gate.check(ROOT)
        for problem in problems:
            print(f"FAIL {problem}")
        print("gate passed" if not problems else f"gate failed ({len(problems)} problems)")
        return 1 if problems else 0
    if args.command == "baseline":
        result = gate.make_baseline(ROOT, args.run)
        (ROOT / "baseline.json").write_text(
            result.model_dump_json(indent=1) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"baseline set to {args.run}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
