"""PLN-36: synthetic unit fixtures, never production release evidence."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "verify_release", Path(__file__).resolve().parents[2] / "scripts/verify_release.py"
)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
pytestmark = pytest.mark.unit
SHA = "a" * 40


@pytest.fixture
def candidate(tmp_path):
    (tmp_path / "frontend").mkdir()
    (tmp_path / "backend/app").mkdir(parents=True)
    (tmp_path / "backend/app/main.py").write_text('app = FastAPI(version="1.0.0")')
    for file, value in [
        ("package.json", {"version": "1.0.0"}),
        ("package-lock.json", {"version": "1.0.0", "packages": {"": {"version": "1.0.0"}}}),
    ]:
        (tmp_path / "frontend" / file).write_text(json.dumps(value))
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "test-summary-report-v1.0.0.pdf").write_bytes(
        b"%PDF-1.4\nsynthetic unit fixture\n%%EOF"
    )
    (bundle / "test-summary-report-v1.0.0.html").write_text(
        f"<h1>Test Summary Report v1.0.0 {SHA}</h1>"
    )
    report = {
        "version": "v1.0.0",
        "commit": SHA,
        "release": {"version": "v1.0.0"},
        "gate": {"gate_passed": True},
        "totals": {
            "total_cases": 3,
            "executed_cases": 2,
            "passed": 2,
            "failed": 0,
            "not_run": 1,
            "pass_rate": 100,
            "execution_rate": 66.7,
            "requirement_coverage": 100,
        },
    }
    (bundle / "test-summary-report-v1.0.0.json").write_text(json.dumps(report))
    (bundle / "release-notes-v1.0.0.md").write_text(f"# v1.0.0\nCommit: {SHA}")
    images = tmp_path / "images.json"
    images.write_text(
        json.dumps(
            [
                {"component": c, "tag": f"sds06/{c}:v1.0.0", "image_id": "sha256:" + str(i) * 64}
                for i, c in enumerate(["backend", "frontend"])
            ]
        )
    )
    return dict(
        root=tmp_path,
        bundle=bundle,
        images_path=images,
        version="v1.0.0",
        commit=SHA,
        output=tmp_path / "verified",
    )


def test_success_manifest_and_checksums(candidate):
    manifest = verifier.verify(**candidate)
    assert manifest["commit"] == SHA and len(manifest["assets"]) == 4
    for line in (candidate["output"] / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ")
        path = (
            candidate["output"] if name == "release-manifest.json" else candidate["bundle"]
        ) / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


@pytest.mark.parametrize(
    "change",
    [
        "tag",
        "commit",
        "lock",
        "backend",
        "missing",
        "pdf",
        "gate",
        "report_commit",
        "rate",
        "nan",
        "images",
        "image_tag",
        "symlink",
    ],
)
def test_invalid_candidate_is_not_manifested(candidate, change):
    root, bundle = candidate["root"], candidate["bundle"]
    report_path = bundle / "test-summary-report-v1.0.0.json"
    report = json.loads(report_path.read_text())
    if change == "tag":
        candidate["version"] = "v1.0.0;bad"
    elif change == "commit":
        candidate["commit"] = "main"
    elif change == "lock":
        (root / "frontend/package-lock.json").write_text('{"version":"0.1.0"}')
    elif change == "backend":
        (root / "backend/app/main.py").write_text('app = FastAPI(version="0.1.0")')
    elif change == "missing":
        (bundle / "test-summary-report-v1.0.0.html").unlink()
    elif change == "pdf":
        (bundle / "test-summary-report-v1.0.0.pdf").write_bytes(b"not a PDF")
    elif change == "gate":
        report["gate"]["gate_passed"] = False
    elif change == "report_commit":
        report["commit"] = "b" * 40
    elif change == "rate":
        report["totals"]["pass_rate"] = 50
    elif change == "nan":
        report["totals"]["execution_rate"] = float("nan")
    elif change == "images":
        candidate["images_path"].write_text("[]")
    elif change == "image_tag":
        candidate["images_path"].write_text(
            json.dumps(
                [
                    {"component": c, "tag": f"sds06/{c}:latest", "image_id": "sha256:" + "0" * 64}
                    for c in ["backend", "frontend"]
                ]
            )
        )
    elif change == "symlink":
        path = bundle / "test-summary-report-v1.0.0.html"
        path.unlink()
        path.symlink_to(report_path)
    report_path.write_text(json.dumps(report))
    with pytest.raises(verifier.InvalidRelease):
        verifier.verify(**candidate)
    assert not candidate["output"].exists()


def test_previous_manifest_is_not_reused(candidate):
    verifier.verify(**candidate)
    before = (candidate["output"] / "release-manifest.json").read_bytes()
    with pytest.raises(verifier.InvalidRelease, match="fresh verification output"):
        verifier.verify(**candidate)
    assert (candidate["output"] / "release-manifest.json").read_bytes() == before


def test_execution_rate_must_match_counts(candidate):
    path = candidate["bundle"] / "test-summary-report-v1.0.0.json"
    data = json.loads(path.read_text())
    data["totals"]["execution_rate"] = 0
    path.write_text(json.dumps(data))
    with pytest.raises(verifier.InvalidRelease, match="execution rate"):
        verifier.verify(**candidate)
    assert not candidate["output"].exists()
