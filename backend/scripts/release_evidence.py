"""PLN-36: application verification report from actual, hash-bound test evidence.

This is distinct from the generator's demo-project preview. It does not change
any project/test/defect status in a database.
"""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from defusedxml.ElementTree import fromstring
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Reviewed acceptance witnesses, not inferred from migrated demo-case statuses.
REQUIREMENTS = {
    "R1": ("test_test_plan_crud_and_workflow",),
    "R2": ("test_test_case_crud_and_specification_fields", "test_test_run_and_execution_lifecycle"),
    "R3": ("test_test_plan_snapshots_and_html_pdf_export",),
    "R4": (
        "test_defect_lifecycle_and_history",
        "test_defect_close_requires_passed_verification_execution",
    ),
    "R5": ("test_release_aggregates_no_fanout_and_first_resolution",),
    "R6": ("test_import_persists_metadata_mapping_outcomes_and_unmatched_report",),
    "R7": ("test_release_exit_gate_criteria_waiver_and_status",),
    "R8": ("test_mutations_require_login_and_role", "test_postgresql_history_is_append_only"),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def xml(path):
    if not 0 < path.stat().st_size <= 20 * 1024 * 1024:
        raise ValueError("Test evidence must be nonempty and <=20 MiB")
    return fromstring(
        path.read_bytes(), forbid_dtd=True, forbid_entities=True, forbid_external=True
    )


def summarize(junit, coverage, evidence, commit):
    provenance = json.loads(evidence.read_text())
    if provenance != {
        "commit": commit,
        "junit_sha256": digest(junit),
        "coverage_sha256": digest(coverage),
    }:
        raise ValueError("Evidence commit/hash mismatch")
    root = xml(junit)
    cases = list(root.iter("testcase"))
    if not cases:
        raise ValueError("No actual JUnit test results")
    results = []
    for case in cases:
        status = (
            "Failed"
            if case.find("failure") is not None or case.find("error") is not None
            else "Skipped"
            if case.find("skipped") is not None
            else "Passed"
        )
        results.append(
            {"name": case.get("name", ""), "classname": case.get("classname", ""), "status": status}
        )
    coverage_root = xml(coverage)
    line_rate, branch_rate = [float(coverage_root.attrib[k]) for k in ("line-rate", "branch-rate")]
    if not all(0 <= r <= 1 for r in (line_rate, branch_rate)):
        raise ValueError("Invalid coverage rates")
    features = []
    for req, witnesses in REQUIREMENTS.items():
        matching = [r for r in results if r["name"].split("[", 1)[0] in witnesses]
        present = {r["name"].split("[", 1)[0] for r in matching}
        verified = set(witnesses) <= present and all(r["status"] == "Passed" for r in matching)
        features.append(
            {
                "id": req,
                "witnesses": list(witnesses),
                "verified": verified,
                "results": matching,
                "missing": sorted(set(witnesses) - present),
            }
        )
    passed = sum(r["status"] == "Passed" for r in results)
    failed = sum(r["status"] == "Failed" for r in results)
    skipped = sum(r["status"] == "Skipped" for r in results)
    req_rate = round(sum(f["verified"] for f in features) / len(features) * 100, 1)
    criteria = {
        "no_failed_tests": failed == 0,
        "has_passed_tests": passed > 0,
        "requirement_coverage": req_rate >= 80,
        "code_line_coverage": line_rate >= 0.8,
        "code_branch_coverage": branch_rate >= 0.8,
    }
    return {
        "totals": {
            "total_cases": len(results),
            "executed_cases": passed + failed,
            "passed": passed,
            "failed": failed,
            "not_run": skipped,
            "execution_rate": round((passed + failed) / len(results) * 100, 1),
            "pass_rate": round(passed / (passed + failed) * 100, 1) if passed + failed else 0,
            "requirement_coverage": req_rate,
        },
        "feature_results": features,
        "results": results,
        "code_coverage": {"line_rate": line_rate, "branch_rate": branch_rate},
        "evidence": provenance,
        "gate": {"gate_passed": all(criteria.values()), "criteria": criteria},
        "scope": "SDS-06 application's own verification suite, not demo-project or production defect inventory",
    }


def build_bundle(output, version, commit, junit, coverage, evidence):
    if not re.fullmatch(r"v\d+\.\d+\.\d+", version) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected a stable version and full candidate commit")
    from weasyprint import HTML

    payload = summarize(junit, coverage, evidence, commit)
    payload.update(
        {
            "identifier": f"TSR-SDS-06-{version}",
            "version": version,
            "commit": commit,
            "release": {"version": version},
            "generated_by": "hash-bound-ci-test-evidence",
            "generated_at": datetime.now(UTC).isoformat(),
        }
    )
    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent), autoescape=select_autoescape(["html", "j2"])
    )
    html = env.get_template("release_evidence.html.j2").render(**payload)
    pdf = HTML(string=html).write_pdf()
    if not pdf.startswith(b"%PDF-"):
        raise ValueError("Test Summary Report PDF rendering failed")
    output.mkdir(parents=True, exist_ok=True)
    for suffix, data in (
        ("html", html.encode()),
        ("pdf", pdf),
        ("json", (json.dumps(payload, indent=2) + "\n").encode()),
    ):
        (output / f"test-summary-report-{version}.{suffix}").write_bytes(data)
    notes = f"# SDS-06 {version}\n\nCommit: `{commit}`\n\nScope: {payload['scope']}\n\n"
    notes += f"Test results: {payload['totals']}\n\nRelease gate passed: {payload['gate']['gate_passed']}\n\n"
    notes += "Required assets: Test Summary Report PDF/HTML/JSON, release-manifest.json and SHA256SUMS.\n"
    (output / f"release-notes-{version}.md").write_text(notes)
    return payload
