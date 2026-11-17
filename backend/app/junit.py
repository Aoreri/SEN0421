"""PLN-22: bounded, entity-safe JUnit parsing; no database side effects."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import Element, ParseError

from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]
from defusedxml.ElementTree import fromstring  # type: ignore[import-untyped]

MAX_XML_BYTES = 1024 * 1024
MAX_RESULTS = 5000


@dataclass(frozen=True)
class JUnitResult:
    name: str
    classname: str
    suite: str
    key: str
    status: str
    duration_seconds: float | None
    message: str


def tag(element: Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def bounded(value: str, limit: int, field: str) -> str:
    if len(value) > limit or "\x00" in value:
        raise ValueError(f"Geçersiz JUnit {field}")
    return value


def parse_case(case: Element, suite: str) -> JUnitResult:
    name = bounded(case.get("name", "").strip(), 512, "name")
    if not name:
        raise ValueError("JUnit testcase name boş olamaz")
    classname = bounded(case.get("classname", ""), 512, "classname")
    keys = [p.get("value", "").strip()
            for props in case if tag(props) == "properties"
            for p in props if tag(p) == "property" and p.get("name") == "test_case_id"]
    if len(keys) > 1 or (keys and not keys[0]):
        raise ValueError("JUnit test_case_id tek ve boş olmayan bir değer olmalı")
    key = bounded(keys[0] if keys else name, 512, "test_case_id")
    outcomes = [child for child in case if tag(child) in ("failure", "error", "skipped")]
    failed = any(tag(child) in ("failure", "error") for child in outcomes)
    skipped = any(tag(child) == "skipped" for child in outcomes)
    if failed and skipped:
        raise ValueError("JUnit sonucu hem başarısız hem atlandı olamaz")
    status = "Failed" if failed else "Skipped" if skipped else "Passed"
    duration = None
    if case.get("time") is not None:
        try:
            value = Decimal(bounded(case.get("time", ""), 32, "time"))
        except InvalidOperation:
            raise ValueError("Geçersiz JUnit time") from None
        if not value.is_finite() or value < 0 or value > Decimal("1e12"):
            raise ValueError("Geçersiz JUnit time")
        duration = float(value)
    message = "\n".join("\n".join(filter(None, [child.get("message", ""),
                                               "".join(child.itertext())])) for child in outcomes)
    bounded(message, MAX_XML_BYTES, "message")
    return JUnitResult(name, classname, suite, key, status, duration, message)


def parse_junit(data: bytes) -> list[JUnitResult]:
    if len(data) > MAX_XML_BYTES:
        raise ValueError("JUnit XML en fazla 1 MiB olabilir")
    try:
        root = fromstring(data, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except (ParseError, DefusedXmlException, ValueError):
        raise ValueError("Geçersiz veya güvenli olmayan JUnit XML") from None
    if tag(root) not in ("testsuite", "testsuites"):
        raise ValueError("JUnit kökü testsuite veya testsuites olmalı")
    # Reject hidden results instead of accepting only a partial report.
    for parent in root.iter():
        for child in parent:
            if tag(child) in ("testsuite", "testsuites", "testcase") and tag(parent) not in (
                "testsuite", "testsuites",
            ):
                raise ValueError("JUnit suite/testcase desteklenmeyen bir öğe içinde")
    results = []
    stack = [(root, "")]
    while stack:
        element, parent_suite = stack.pop()
        kind = tag(element)
        if kind == "testcase":
            results.append(parse_case(element, parent_suite))
            if len(results) > MAX_RESULTS:
                raise ValueError("JUnit en fazla 5000 sonuç içerebilir")
        elif kind in ("testsuite", "testsuites"):
            suite = bounded(element.get("name", parent_suite), 512, "suite")
            for child in reversed(list(element)):
                if tag(child) == "testcase" and kind != "testsuite":
                    raise ValueError("JUnit testcase bir testsuite içinde olmalı")
                if tag(child) in ("testsuite", "testsuites", "testcase"):
                    stack.append((child, suite))
    if not results:
        raise ValueError("JUnit XML test sonucu içermiyor")
    return results
