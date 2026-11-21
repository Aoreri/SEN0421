"""PLN-22/R6: JUnit structure, outcome semantics and safe input handling."""
import pytest

from app.junit import MAX_XML_BYTES, parse_junit

pytestmark = pytest.mark.unit


def test_nested_namespaced_suites_keep_result_order_and_actual_counts():
    results = parse_junit(b'''<testsuites xmlns="urn:junit" tests="999">
      <testsuite name="outer">
        <testcase name="TC-001" time="0.125"/>
        <testsuite name="inner"><testcase name="TC-002"><failure message="bad">details</failure></testcase></testsuite>
        <testcase name="T…870 tokens truncated…0].suite == "inner"


def test_failure_signature_ignores_presentation_but_retains_kind_type_and_diagnostics():
    first = parse_junit(b'''<testsuite><testcase name="a"><failure type="AssertionError"
      message="expected 200">actual 500</failure></testcase></testsuite>''')[0]
    formatted = parse_junit(b'''<testsuite name="other"><testcase name="b" time="5">
      <failure type="AssertionError" message=" expected   200 "> actual\n 500 </failure>
      </testcase></testsuite>''')[0]
    assert first.failure_signature == formatted.failure_signature
    for xml in (
        b'<testsuite><testcase name="a"><error type="AssertionError" message="expected 200">actual 500</error></testcase></testsuite>',
        b'<testsuite><testcase name="a"><failure type="Timeout" message="expected 200">actual 500</failure></testcase></testsuite>',
        b'<testsuite><testcase name="a"><failure type="AssertionError" message="expected 200">actual 403</failure></testcase></testsuite>',
    ):
        assert parse_junit(xml)[0].failure_signature != first.failure_signature
    assert parse_junit(b'<testsuite><testcase name="a"/></testsuite>')[0].failure_signature is None
