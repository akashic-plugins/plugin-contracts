from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contract import check_plugin


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="akashic-plugin-contract")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check")
    check.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)

    reports = [check_plugin(path) for path in args.paths]
    print(
        json.dumps(
            {
                "contract": "akashic-plugin-api-v2",
                "passed": all(report.passed for report in reports),
                "reports": [report.to_dict() for report in reports],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if all(report.passed for report in reports) else 1
