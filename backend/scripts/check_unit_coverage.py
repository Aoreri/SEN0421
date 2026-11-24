"""PLN-35: enforce >=80% line AND branch coverage separately for each module."""
import argparse
import json
from pathlib import Path

MODULES = ("app/main.py", "app/runs.py", "app/metrics.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    failures = []
    for name in MODULES:
        summary = report["files"][name]["summary"]
        lines = 100 * summary["covered_lines"] / summary["num_statements"]
        branches = 100 * summary["covered_branches"] / summary["num_branches"]
        print(f"{name}: lines={lines:.2f}% branches={branches:.2f}%")
        if min(lines, branches) < 80:
            failures.append(name)
    if failures:
        raise SystemExit("Unit coverage below 80%: " + ", ".join(failures))


if __name__ == "__main__":
    main()
