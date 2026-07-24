from __future__ import annotations

import argparse
import json

from .core import run_stress_test


def main():
    parser = argparse.ArgumentParser(description="Run standalone AI Mouse profile stress tests")
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    report = run_stress_test(args.runs, args.seed)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
