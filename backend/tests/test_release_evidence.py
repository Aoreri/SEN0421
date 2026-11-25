"""PLN-36: synthetic parser fixtures exercise failure paths, not release evidence."""

import hashlib
import json
from xml.etree.ElementTree import Element, SubElement, tostring

import pytest

from scripts.release_evidence import REQUIREMENTS, summarize

pytestmark = pytest.mark.unit
SHA = "a" * 40


@pytest.fixture
def evidence(tmp_path):
    root = Element("testsuites")
    suite = SubElement(root, "testsuite")
    for req, witnesses in REQUIREMENTS.items():
        for name in witnesses:
            SubElement(suite, "testcase", name=name, classname=f"synthetic.{req}")
    junit = tmp_path / "junit.xml"
    junit.write_bytes(tostring(root))
    coverage = tmp_path / "coverage.xml"
    coverage.write_text('<coverage line-rate="0.95" branch-rate="0.90"/>')
    seal = tmp_path / "test-evidence.json"
    return junit, coverage, seal


def run(paths, mutate=None):
    junit, coverage, seal = paths
    seal.write_text(
        json.dumps(
            {
                "commit": SHA,
                "junit_sha256": hashlib.sha256(junit.read_bytes()).hexdigest(),
                "coverage_sha256": hashlib.sha256(coverage.read_bytes()).hexdigest(),
            }
        )
    )
    if mutate:
        mutate()
    return summarize(junit, coverage, seal, SHA)


def test_all_executed_witnesses_and_high_coverage_pass(evidence):
    data = run(evidence)
    assert data["totals"]["requirement_coverage"] == 100
    assert data["gate"]["gate_passed"]
    assert len(data["feature_results"]) == 8


@pytest.mark.parametrize("status", ["failure", "error", "skipped"])
def test_failures_errors_and_skips_are_not_converted_to_passes(evidence, status):
    junit = evidence[0]
    from xml.etree.ElementTree import fromstring

    root = fromstring(junit.read_bytes())
    for case in root.iter("testcase"):
        SubElement(case, status)
    junit.write_bytes(tostring(root))
    data = run(evidence)
    assert not data["gate"]["gate_passed"]
    assert data["totals"]["passed"] == 0
    assert data["totals"]["requirement_coverage"] == 0
    assert data["totals"]["not_run" if status == "skipped" else "failed"] > 0


def test_missing_witnesses_do_not_inherit_seed_requirement_links(evidence):
    evidence[0].write_text('<testsuite><testcase name="unmapped_but_passed"/></testsuite>')
    data = run(evidence)
    assert data["totals"]["passed"] == 1
    assert data["totals"]["requirement_coverage"] == 0
    assert not data["gate"]["gate_passed"]


@pytest.mark.parametrize(
    "xml",
    [
        '<coverage line-rate="0.79" branch-rate="0.99"/>',
        '<coverage line-rate="0.99" branch-rate="0.79"/>',
    ],
)
def test_each_coverage_threshold_is_enforced(evidence, xml):
    evidence[1].write_text(xml)
    assert not run(evidence)["gate"]["gate_passed"]


@pytest.mark.parametrize("changed", [0, 1])
def test_changed_evidence_is_rejected_after_hashing(evidence, changed):
    with pytest.raises(ValueError, match="hash mismatch"):
        run(evidence, lambda: evidence[changed].write_text("changed bytes"))


def test_wrong_commit_cannot_reuse_other_results(evidence):
    run(evidence)
    with pytest.raises(ValueError, match="commit/hash"):
        summarize(*evidence, "b" * 40)


def test_entities_and_empty_results_are_rejected(evidence):
    evidence[0].write_text(
        '<!DOCTYPE x [<!ENTITY t "expansion">]><testsuite><testcase name="&t;"/></testsuite>'
    )
    from defusedxml.common import DefusedXmlException

    with pytest.raises(DefusedXmlException):
        run(evidence)
    evidence[0].write_text("<testsuite/>")
    with pytest.raises(ValueError, match="No actual"):
        run(evidence)
