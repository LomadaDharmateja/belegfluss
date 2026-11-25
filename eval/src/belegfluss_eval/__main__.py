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
    live = commands.add_parser("run", help="live evaluation (costs money): records the answers")
    live.add_argument("--split", choices=["dev", "test"], required=True)
    live.add_argument("--extractor", choices=["azure", "di"], default="azure")
    live.add_argument("--max-usd", type=float, default=2.0)
    live.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    live.add_argument("--image-only", action="store_true", help="ablation: no text layer sent")
    report = commands.add_parser("report", help="write a report for one or more runs")
    report.add_argument("name")
    report.add_argument("runs", nargs="+", help="run folders; the first is the main run")
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
    if args.command == "run":
        from belegfluss_eval import runner

        folder = runner.run(
            args.split, args.extractor, args.max_usd, args.reasoning_effort, args.image_only
        )
        print(f"recorded: {folder.name}")
        return 0
    if args.command == "report":
        from belegfluss_eval import report as report_module

        print(f"written: {report_module.write(args.runs, args.name)}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
