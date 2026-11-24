"""PLN-36/Esra: validate a candidate without tagging, publishing or changing its data."""

import argparse
import ast
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path


class InvalidRelease(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidRelease(message)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise InvalidRelease(f"Invalid JSON: {path.name}") from error


def check_source(root, version):
    expected = version.removeprefix("v")
    package = read_json(root / "frontend/package.json")
    lock = read_json(root / "frontend/package-lock.json")
    require(package.get("version") == expected, "Frontend package version mismatch")
    require(lock.get("version") == expected, "Frontend lockfile version mismatch")
    require(
        lock.get("packages", {}).get("", {}).get("version") == expected,
        "Frontend lockfile root-package version mismatch",
    )
    try:
        module = ast.parse((root / "backend/app/main.py").read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as error:
        raise InvalidRelease("Cannot inspect backend version") from error
    versions = [
        keyword.value.value
        for node in ast.walk(module)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "FastAPI"
        for keyword in node.keywords
        if keyword.arg == "version" and isinstance(keyword.value, ast.Constant)
    ]
    require(versions == [expected], "Backend FastAPI version mismatch")


def verify(
    root, bundle, images_path, version, commit, output, require_test_evidence=False
):
    require(
        re.fullmatch(r"v\d+\.\d+\.\d+", version),
        "Expected a stable version such as v1.0.0",
    )
    require(
        re.fullmatch(r"[0-9a-f]{40}", commit),
        "Expected the full lowercase candidate commit SHA",
    )
    require(
        not (output / "release-manifest.json").exists()
        and not (output / "SHA256SUMS").exists(),
        "Use a fresh verification output; an earlier manifest/checksum file exists",
    )
    check_source(root, version)
    names = [f"test-summary-report-{version}.{ext}" for ext in ("pdf", "html", "json")]
    names.append(f"release-notes-{version}.md")
    source_report = read_json(bundle / names[2])
    if require_test_evidence:
        require(
            source_report.get("generated_by") == "hash-bound-ci-test-evidence",
            "Publication requires actual test evidence, not a demo preview",
        )
    if source_report.get("generated_by") == "hash-bound-ci-test-evidence":
        names.extend(["junit.xml", "coverage.xml", "test-evidence.json"])
    assets = []
    for name in names:
        path = bundle / name
        require(
            path.is_file() and not path.is_symlink(),
            f"Missing or linked release asset: {name}",
        )
        require(
            0 < path.stat().st_size <= 20 * 1024 * 1024,
            f"Empty or oversized release asset: {name}",
        )
        data = path.read_bytes()
        assets.append(
            {
                "name": name,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    pdf = (bundle / names[0]).read_bytes()
    require(
        pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF"),
        "Invalid PDF attachment",
    )
    html = (bundle / names[1]).read_text(encoding="utf-8")
    require("Test Summary Report" in html, "Missing Test Summary Report HTML content")
    notes = (bundle / names[3]).read_text(encoding="utf-8")
    require(
        version in notes and commit in notes,
        "Release notes must identify the version and candidate commit",
    )
    require(
        version in html and commit in html,
        "HTML report must identify the candidate version/commit",
    )
    report = read_json(bundle / names[2])
    require(
        report.get("version") == version and report.get("commit") == commit,
        "Test Summary Report version/commit mismatch",
    )
    require(
        report.get("release", {}).get("version") == version,
        "Report release version mismatch",
    )
    require(
        report.get("gate", {}).get("gate_passed") is True,
        "Release exit gate has not passed",
    )
    if source_report.get("generated_by") == "hash-bound-ci-test-evidence":
        evidence = read_json(bundle / "test-evidence.json")
        expected = {
            "commit": commit,
            **{
                f"{name}_sha256": hashlib.sha256(
                    (bundle / f"{name}.xml").read_bytes()
                ).hexdigest()
                for name in ("junit", "coverage")
            },
        }
        require(
            evidence == expected and report.get("evidence") == expected,
            "Report test-evidence commit/hash mismatch",
        )
    if require_test_evidence:
        source = (
            Path(__file__).resolve().parents[1] / "backend/scripts/release_evidence.py"
        )
        spec = importlib.util.spec_from_file_location("release_evidence_check", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        actual = module.summarize(
            bundle / "junit.xml",
            bundle / "coverage.xml",
            bundle / "test-evidence.json",
            commit,
        )
        require(
            all(
                report.get(key) == actual[key]
                for key in (
                    "totals",
                    "gate",
                    "feature_results",
                    "code_coverage",
                    "results",
                )
            ),
            "Report disagrees with actual JUnit/Cobertura evidence",
        )
    totals = report.get("totals", {})
    for field in ("total_cases", "executed_cases", "passed", "failed", "not_run"):
        value = totals.get(field)
        require(type(value) is int and value >= 0, f"Invalid report total: {field}")
    require(
        totals["total_cases"] > 0,
        "Empty test population cannot establish release readiness",
    )
    require(
        totals["executed_cases"] == totals["passed"] + totals["failed"],
        "Inconsistent executed-case total",
    )
    require(
        totals["executed_cases"] + totals["not_run"] <= totals["total_cases"],
        "Inconsistent total-case population",
    )
    for field in ("pass_rate", "requirement_coverage", "execution_rate"):
        value = totals.get(field)
        require(
            type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 100,
            f"Invalid report percentage: {field}",
        )
    expected_rate = (
        round(totals["passed"] / totals["executed_cases"] * 100, 1)
        if totals["executed_cases"]
        else 0
    )
    require(
        totals["pass_rate"] == expected_rate,
        "Report pass rate disagrees with its own population",
    )
    require(
        totals["execution_rate"]
        == round(totals["executed_cases"] / totals["total_cases"] * 100, 1),
        "Report execution rate disagrees with its own population",
    )
    images = read_json(images_path)
    require(
        isinstance(images, list) and len(images) == 2,
        "Both backend and frontend image records are required",
    )
    require(all(isinstance(image, dict) for image in images), "Invalid image records")
    require(
        {image.get("component") for image in images} == {"backend", "frontend"},
        "Image components must be backend and frontend",
    )
    for image in images:
        require(
            re.fullmatch(r"sha256:[0-9a-f]{64}", image.get("image_id", "")),
            "Invalid built image ID",
        )
        require(
            image.get("tag", "").endswith(f"/{image['component']}:{version}"),
            "Image version/component tag mismatch",
        )
    manifest = {
        "plan_item": "PLN-36",
        "version": version,
        "commit": commit,
        "scope": "candidate source, local built images and report bundle; publication not performed",
        "report_generated_by": report.get("generated_by"),
        "exit_gate_passed": True,
        "assets": assets,
        "images": images,
    }
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    sums = [f"{a['sha256']}  {a['name']}" for a in assets]
    sums.append(
        f"{hashlib.sha256(manifest_path.read_bytes()).hexdigest()}  release-manifest.json"
    )
    (output / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = verify(
            args.root,
            args.bundle,
            args.images,
            args.version,
            args.commit,
            args.output,
            require_test_evidence=True,
        )
    except (InvalidRelease, OSError, TypeError, AttributeError) as error:
        raise SystemExit(f"Release verification failed: {error}") from error
    print(
        f"Verified {manifest['version']} at {manifest['commit']}; no tag or release was published."
    )


if __name__ == "__main__":
    main()
