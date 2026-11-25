"""Command line: `python -m belegfluss_eval <command>` (run in `eval/`)."""

import argparse
import sys

from belegfluss_eval import gate, manifest
from belegfluss_eval.paths import EVAL as ROOT
from belegfluss_eval.paths import MANIFEST


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="belegfluss_eval")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("gate", help="replay the baseline with the current code (CI)")
    baseline = commands.add_parser("baseline", help="make a run the new baseline")
    baseline.add_argument("run", help="folder name in recordings/")
    commands.add_parser(
        "build-dataset", help="render the labelled set and package it (Docker, Chromium)"
    )
    commands.add_parser("fetch", help="download the released dataset and check every file")
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
    if args.command == "build-dataset":
        from belegfluss_eval.dataset import build

        data = build.build()
        archive = build.package()
        counts: dict[str, int] = {}
        for doc in data.documents:
            key = f"{doc.split} {doc.source}/{doc.variant}"
            counts[key] = counts.get(key, 0) + 1
        for key, value in sorted(counts.items()):
            print(f"{key:<28}{value:>4}")
        print(f"documents {len(data.documents)}, dataset version {manifest.version(MANIFEST)[:12]}")
        print(f"{archive.name}: {build._sha256(archive)}")
        return 0
    if args.command == "fetch":
        from belegfluss_eval.dataset import build

        problems = build.fetch()
        for problem in problems:
            print(f"FAIL {problem}")
        print("dataset ok" if not problems else f"{len(problems)} problems")
        return 1 if problems else 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
