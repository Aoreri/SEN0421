"""PLN-23: bounded Cobertura counters computed from file/line evidence."""
import re
from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]
from defusedxml.ElementTree import fromstring  # type: ignore[import-untyped]

MAX_COVERAGE_BYTES = 4 * 1024 * 1024
MAX_COVERAGE_LINES = 50000
MAX_COVERAGE_FILES = 5000


def integer(value: str | None, field: str, minimum: int = 0) -> int:
    if value is None or not re.fullmatch(r"[0-9]{1,10}", value):
        raise ValueError(f"Invalid Cobertura {field}")
    number = int(value)
    if number < minimum:
        raise ValueError(f"Invalid Cobertura {field}")
    return number


def percentage(covered: int, valid: int) -> float:
    return round(covered / valid * 100, 1) if valid else 0.0


def parse_cobertura(data: bytes) -> dict:
    if len(data) > MAX_COVERAGE_BYTES:
        raise ValueError("Cobertura XML exceeds 4 MiB")
    try:
        # coverage.py emits a standard external DOCTYPE. ElementTree never fetches
        # that DTD; entity declarations and external entity references are forbidden.
        root = fromstring(data, forbid_entities=True, forbid_external=True)
    except (ParseError, DefusedXmlException, ValueError):
        raise ValueError("Invalid or unsafe Cobertura XML") from None
    if root.tag != "coverage":
        raise ValueError("Cobertura root must be coverage")
    files: dict[str, dict] = {}
    count = 0
    for cls in root.findall("./packages/package/classes/class"):
        filename = cls.get("filename", "").replace("\\", "/")
        if (not filename or len(filename) > 512 or filename.startswith("/")
                or ":" in filename or any(ord(c) < 32 for c in filename)
                or any(part in ("", ".", "..") for part in filename.split("/"))):
            raise ValueError("Invalid Cobertura relative filename")
        entry = files.setdefault(filename, {"filename": filename, "lines_valid": 0,
            "lines_covered": 0, "branches_valid": 0, "branches_covered": 0, "seen": set()})
        if len(files) > MAX_COVERAGE_FILES:
            raise ValueError("Cobertura exceeds 5000 files")
        for line in cls.findall("./lines/line"):
            count += 1
            if count > MAX_COVERAGE_LINES:
                raise ValueError("Cobertura exceeds 50000 lines")
            number = integer(line.get("number"), "line number", 1)
            hits = integer(line.get("hits"), "hits")
            if number in entry["seen"]:
                raise ValueError("Duplicate Cobertura file/line")
            entry["seen"].add(number)
            entry["lines_valid"] += 1
            entry["lines_covered"] += int(hits > 0)
            if line.get("branch", "false") not in ("true", "false"):
                raise ValueError("Invalid Cobertura branch flag")
            if line.get("branch") == "true":
                match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)% \(([0-9]+)/([0-9]+)\)",
                                     line.get("condition-coverage", ""))
                if match is None:
                    raise ValueError("Missing Cobertura branch evidence")
                covered = integer(match[2], "covered branches")
                valid = integer(match[3], "valid branches", 1)
                if covered > valid or abs(float(match[1]) - covered / valid * 100) > 1.0:
                    raise ValueError("Inconsistent Cobertura branch evidence")
                entry["branches_valid"] += valid
                entry["branches_covered"] += covered
    # Do not ignore line evidence hidden in unsupported structures (e.g. wrappers).
    # Method lines are redundant in standard Cobertura and are not counted twice.
    class_lines = sum(len(cls.findall("./lines/line")) for cls in
                      root.findall("./packages/package/classes/class"))
    all_nonmethod = sum(1 for lines in root.iter("lines") for child in lines
                       if child.tag == "line")
    method_lines = sum(len(method.findall("./lines/line")) for method in root.iter("method"))
    if all_nonmethod - method_lines != class_lines:
        raise ValueError("Unsupported Cobertura line structure")
    keys = ("lines_valid", "lines_covered", "branches_valid", "branches_covered")
    summary = {key: sum(entry[key] for entry in files.values()) for key in keys}
    for key in keys:
        reported = integer(root.get(key.replace("_", "-")), key)
        if reported != summary[key]:
            raise ValueError(f"Cobertura {key} does not match line evidence")
    for attr, covered_key, valid_key in (("line-rate", "lines_covered", "lines_valid"),
                                  ("branch-rate", "branches_covered", "branches_valid")):
        if root.get(attr) is not None:
            try:
                rate = Decimal(root.get(attr, ""))
            except InvalidOperation:
                raise ValueError(f"Invalid Cobertura {attr}") from None
            expected = Decimal(summary[covered_key]) / Decimal(summary[valid_key]) if summary[valid_key] else Decimal(0)
            if (not rate.is_finite() or not 0 <= rate <= 1
                    or (summary[valid_key] and abs(rate - expected) > Decimal("0.0001"))):
                raise ValueError(f"Inconsistent Cobertura {attr}")
    result_files = []
    for entry in sorted(files.values(), key=lambda row: row["filename"]):
        del entry["seen"]
        entry["line_coverage"] = percentage(entry["lines_covered"], entry["lines_valid"])
        entry["branch_coverage"] = percentage(entry["branches_covered"], entry["branches_valid"])
        result_files.append(entry)
    return {"summary": {**summary,
            "line_coverage": percentage(summary["lines_covered"], summary["lines_valid"]),
            "branch_coverage": percentage(summary["branches_covered"], summary["branches_valid"])},
            "files": result_files}
