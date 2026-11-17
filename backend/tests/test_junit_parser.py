"""PLN-22/R6: JUnit structure, outcome semantics and safe input handling."""
import pytest

from app.junit import MAX_XML_BYTES, parse_junit

pytestmark = pytest.mark.unit


def test_nested_namespaced_suites_keep_result_order_and_actual_counts():
    results = parse_junit(b'''<testsuites xmlns="urn:junit" tests="999">
      <testsuite name="outer">
        <testcase name="TC-001" time="0.125"/>
        <testsuite name="inner"><testcase name="TC-002"><failure message="bad">details</failure></testcase></testsuite>
        <testcase name="TC-003"><error message="execution error"/></testcase>
        <testcase name="TC-004"><skipped message="not selected"/></testcase>
      </testsuite></testsuites>''')
    assert [r.key for r in results] == ["TC-001", "TC-002", "TC-003", "TC-004"]
    assert [r.status for r in results] == ["Passed", "Failed", "Failed", "Skipped"]
    assert results[0].duration_seconds == 0.125
    assert results[1].suite == "inner"
    assert results[1].message == "bad\ndetails"


def test_explicit_stable_key_has_priority_over_name_and_duplicates_are_retained():
    results = parse_junit(b'''<testsuite><testcase name="test_login[param]">
      <properties><property name="test_case_id" value="TC-001"/></properties>
      </testcase><testcase name="TC-001"/></testsuite>''')
    assert [r.key for r in results] == ["TC-001", "TC-001"]
    assert results[0].name == "test_login[param]"


@pytest.mark.parametrize("xml", [
    b"", b"<testsuite>", b"<html/>", b"<testsuite/>",
    b'<testsuites><testcase name="TC-001"/></testsuites>',
    b'<testsuite><testcase/></testsuite>',
    b'<testsuite><testcase name="x"><failure/><skipped/></testcase></testsuite>',
    b'<testsuite><testcase name="x"><properties><property name="test_case_id" value=""/></properties></testcase></testsuite>',
    b'<testsuite><testcase name="x"><properties><property name="test_case_id" value="a"/><property name="test_case_id" value="b"/></properties></testcase></testsuite>',
    b'<!DOCTYPE testsuite [<!ENTITY x "boom">]><testsuite><testcase name="&x;"/></testsuite>',
    b'<!DOCTYPE testsuite SYSTEM "https://example.invalid/external.dtd"><testsuite><testcase name="x"/></testsuite>',
])
def test_invalid_or_entity_bearing_input_is_rejected(xml):
    with pytest.raises(ValueError):
        parse_junit(xml)


@pytest.mark.parametrize("duration", ["-1", "NaN", "Infinity", "not-a-number", "1e100", ""])
def test_invalid_duration_is_rejected(duration):
    with pytest.raises(ValueError):
        parse_junit(f'<testsuite><testcase name="x" time="{duration}"/></testsuite>'.encode())


def test_name_and_result_count_limits():
    with pytest.raises(ValueError):
        parse_junit(('<testsuite><testcase name="' + 'a' * 513 + '"/></testsuite>').encode())
    with pytest.raises(ValueError):
        parse_junit(b'<testsuite>' + b'<testcase name="x"/>' * 5001 + b'</testsuite>')
    with pytest.raises(ValueError):
        parse_junit(b' ' * (MAX_XML_BYTES + 1))


@pytest.mark.parametrize("hidden", [
    '<wrapper><testcase name="TC-002"/></wrapper>',
    '<wrapper><testsuite><testcase name="TC-002"/></testsuite></wrapper>',
    '<testcase name="TC-002"><testcase name="TC-003"/></testcase>',
])
def test_hidden_results_reject_the_entire_report(hidden):
    xml = f'<testsuite><testcase name="TC-001"/>{hidden}</testsuite>'
    with pytest.raises(ValueError, match="desteklenmeyen"):
        parse_junit(xml.encode())


def test_namespaced_nested_suites_and_metadata_remain_supported():
    results = parse_junit(b'''<testsuites xmlns="urn:junit"><testsuite name="outer">
      <properties><property name="build" value="42"/></properties>
      <testsuite name="inner"><testcase name="TC-001"/><system-out>log</system-out></testsuite>
      </testsuite></testsuites>''')
    assert len(results) == 1 and results[0].suite == "inner"
