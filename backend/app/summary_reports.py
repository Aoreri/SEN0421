"""IEEE 829 Test Summary Report (ISO/IEC/IEEE 29119-3 Test Completion Report) üretimi ve snapshot saklama (PLN-30)."""
import importlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from .auth import ADMIN, TEST_LEAD, TESTER, require_roles
from .db import DB
from .models import (
    Defect,
    Project,
    Release,
    Requirement,
    TestCase,
    TestExecution,
    TestRun,
    TestSuite,
    TestSummaryReportSnapshot,
    User,
    execution_defects,
)
from .projects import get_or_404, release_gate_out
from .test_plans import _pdf_escape

router = APIRouter(prefix="/api/releases", tags=["test-summary-reports"])
SnapshotUser = Annotated[User, Depends(require_roles(ADMIN, TEST_LEAD, TESTER))]

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "j2"]),
)

SEVERITIES = ("Critical", "High", "Medium", "Low")


def _fmt_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def snapshot_summary_out(s: TestSummaryReportSnapshot) -> dict[str, Any]:
    return {
        "id": s.id,
        "release_id": s.release_id,
        "release_version": s.release_version,
        "release_status": s.release_status,
        "gate_passed": s.gate_passed,
        "generated_by": s.generated_by,
        "generated_at": s.generated_at,
    }


def snapshot_detail_out(s: TestSummaryReportSnapshot) -> dict[str, Any]:
    return {
        **snapshot_summary_out(s),
        "html_content": s.html_content,
        "payload": s.payload,
    }


def build_summary_report_data(
    db: Session, release: Release, generated_by: str
) -> tuple[str, dict[str, Any]]:
    project = db.get(Project, release.project_id)
    assert project is not None

    gate = release_gate_out(db, release)
    gate = {**gate, "actual_pass_rate_basis": "project_catalogue_status"}
    if gate["waiver"] is not None and isinstance(gate["waiver"].get("waived_at"), datetime):
        gate = {
            **gate,
            "waiver": {
                **gate["waiver"],
                "waived_at": _fmt_dt(gate["waiver"]["waived_at"]),
            },
        }

    reqs = list(
        db.scalars(
            select(Requirement)
            .options(selectinload(Requirement.test_cases))
            .where(Requirement.project_id == release.project_id)
            .order_by(Requirement.id)
        )
    )
    suites = list(
        db.scalars(
            select(TestSuite)
            .options(selectinload(TestSuite.test_cases))
            .where(TestSuite.project_id == release.project_id)
            .order_by(TestSuite.id)
        )
    )

    project_case_filter = or_(
        TestCase.requirements.any(Requirement.project_id == release.project_id),
        TestCase.suite.has(TestSuite.project_id == release.project_id),
    )
    project_cases = list(
        db.scalars(
            select(TestCase)
            .where(project_case_filter)
            .options(selectinload(TestCase.requirements))
            .order_by(TestCase.id)
        )
    )

    release_runs = list(
        db.scalars(
            select(TestRun)
            .options(selectinload(TestRun.executions))
            .where(TestRun.release_id == release.id)
            .order_by(TestRun.id)
        )
    )

    # If the release has dedicated interactive test runs, compute latest status per case from those runs;
    # otherwise fall back to the project's test case catalogue statuses (consistent with release_gate_out).
    latest_release_status: dict[str, str] = {}
    release_execution_count = 0
    for run in release_runs:
        for ex in run.executions:
            release_execution_count += 1
            if ex.status != "Not Run" or ex.test_case_id not in latest_release_status:
                latest_release_status[ex.test_case_id] = ex.status

    def effective_status(tc: TestCase) -> str:
        if tc.id in latest_release_status:
            return latest_release_status[tc.id]
        return tc.status

    status_counts = {"Passed": 0, "Failed": 0, "Blocked": 0, "Skipped": 0, "Not Run": 0}
    for tc in project_cases:
        st = effective_status(tc)
        status_counts[st] = status_counts.get(st, 0) + 1

    total_cases = len(project_cases)
    executed_cases = status_counts["Passed"] + status_counts["Failed"]
    decisive = executed_cases
    covered_reqs = sum(1 for req in reqs if req.test_cases)

    totals = {
        "total_cases": total_cases,
        "executed_cases": executed_cases,
        "passed": status_counts["Passed"],
        "failed": status_counts["Failed"],
        "blocked": status_counts["Blocked"],
        "skipped": status_counts["Skipped"],
        "not_run": status_counts["Not Run"],
        "execution_rate": round(executed_cases / total_cases * 100, 1) if total_cases else 0.0,
        "pass_rate": round(status_counts["Passed"] / decisive * 100, 1) if decisive else 0.0,
        "pass_rate_basis": "release_runs_with_catalogue_fallback",
        "total_requirements": len(reqs),
        "covered_requirements": covered_reqs,
        "requirement_coverage": gate["actual_req_coverage"],
        "run_count": len(release_runs),
        "release_execution_count": release_execution_count,
    }

    feature_results: list[dict[str, Any]] = []
    for req in reqs:
        req_cases = sorted(req.test_cases, key=lambda c: c.id)
        r_counts = {"Passed": 0, "Failed": 0, "Blocked": 0, "Skipped": 0, "Not Run": 0}
        for tc in req_cases:
            st = effective_status(tc)
            r_counts[st] = r_counts.get(st, 0) + 1
        if not req_cases:
            assessment = "Kapsam Eksik (Test Yok)"
        elif r_counts["Failed"] > 0:
            assessment = "Başarısız (Failed)"
        elif r_counts["Passed"] == len(req_cases):
            assessment = "Doğrulandı (Passed)"
        elif r_counts["Passed"] > 0:
            assessment = "Kısmi Doğrulandı"
        else:
            assessment = "Henüz Koşulmadı"
        feature_results.append(
            {
                "id": req.id,
                "title": req.title,
                "description": req.description,
                "test_cases": [c.id for c in req_cases],
                "total_cases": len(req_cases),
                "passed": r_counts["Passed"],
                "failed": r_counts["Failed"],
                "blocked": r_counts["Blocked"],
                "skipped": r_counts["Skipped"],
                "not_run": r_counts["Not Run"],
                "assessment": assessment,
            }
        )

    suite_results: list[dict[str, Any]] = []
    for s in suites:
        s_cases = sorted(s.test_cases, key=lambda c: c.id)
        s_counts = {"Passed": 0, "Failed": 0, "Blocked": 0, "Skipped": 0, "Not Run": 0}
        for tc in s_cases:
            st = effective_status(tc)
            s_counts[st] = s_counts.get(st, 0) + 1
        suite_results.append(
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "total_cases": len(s_cases),
                "passed": s_counts["Passed"],
                "failed": s_counts["Failed"],
                "blocked": s_counts["Blocked"],
                "skipped": s_counts["Skipped"],
                "not_run": s_counts["Not Run"],
            }
        )

    other_project_case_ids = select(TestCase.id).where(
        ~project_case_filter,
        or_(
            TestCase.requirements.any(Requirement.project_id != release.project_id),
            TestCase.suite.has(TestSuite.project_id != release.project_id),
        ),
    )
    other_project_exec_defect_ids = (
        select(execution_defects.c.defect_id)
        .join(TestExecution, TestExecution.id == execution_defects.c.execution_id)
        .join(TestRun, TestRun.id == TestExecution.run_id)
        .where(TestRun.project_id != release.project_id)
    )
    project_exec_defect_ids = (
        select(execution_defects.c.defect_id)
        .join(TestExecution, TestExecution.id == execution_defects.c.execution_id)
        .join(TestRun, TestRun.id == TestExecution.run_id)
        .where(TestRun.project_id == release.project_id)
    )
    defect_branches: list[Any] = [
        Defect.test_case.in_(select(TestCase.id).where(project_case_filter)),
        Defect.id.in_(project_exec_defect_ids),
        Defect.test_case.is_(None) & ~Defect.id.in_(other_project_exec_defect_ids),
    ]
    project_defect_filter = or_(*defect_branches) & or_(
        Defect.test_case.is_(None), ~Defect.test_case.in_(other_project_case_ids)
    )

    defects = list(db.scalars(select(Defect).where(project_defect_filter).order_by(Defect.id)))
    defect_dicts = [
        {
            "id": d.id,
            "title": d.title,
            "severity": d.severity,
            "status": d.status,
            "test_case": d.test_case,
        }
        for d in defects
    ]

    by_severity: list[dict[str, Any]] = []
    # The API accepts any severity string, so list non-standard ones after the canonical four.
    extra_severities = sorted({d.severity for d in defects} - set(SEVERITIES))
    for sev in (*SEVERITIES, *extra_severities):
        sev_defs = [d for d in defects if d.severity == sev]
        open_cnt = sum(1 for d in sev_defs if d.status != "Closed")
        closed_cnt = sum(1 for d in sev_defs if d.status == "Closed")
        by_severity.append(
            {
                "severity": sev,
                "total": len(sev_defs),
                "open": open_cnt,
                "closed": closed_cnt,
            }
        )

    defect_summary = {
        "total": len(defects),
        "open_total": sum(1 for d in defects if d.status != "Closed"),
        "closed_total": sum(1 for d in defects if d.status == "Closed"),
        "open_critical": gate["actual_open_critical"],
        "by_severity": by_severity,
    }

    generated_at_iso = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    identifier = f"TSR-{project.name}-{release.version}"
    payload: dict[str, Any] = {
        "identifier": identifier,
        "generated_by": generated_by,
        "generated_at": generated_at_iso,
        "project": {"id": project.id, "name": project.name, "description": project.description},
        "release": {"id": release.id, "version": release.version, "status": release.status},
        "totals": totals,
        "feature_results": feature_results,
        "suite_results": suite_results,
        "defect_summary": defect_summary,
        "defects": defect_dicts,
        "gate": gate,
    }
    template = jinja_env.get_template("test_summary_report.html.j2")
    html_content = template.render(**payload)
    return html_content, payload


def _fallback_summary_pdf_bytes(payload: dict[str, Any]) -> bytes:
    """RSK-07 fallback: WeasyPrint / GTK bulunmadığında standart uyumlu %PDF-1.4 üretir."""
    project = payload["project"]
    release = payload["release"]
    totals = payload["totals"]
    gate = payload["gate"]
    defect_summary = payload["defect_summary"]

    lines: list[str] = [
        f"IEEE 829 / ISO/IEC/IEEE 29119-3 TEST SUMMARY REPORT: {payload['identifier']}",
        f"Project: {project['name']} | Release: {release['version']} (Status: {release['status']})",
        f"Release Gate: {'PASSED' if gate['gate_passed'] else 'BLOCKED'}",
        f"Generated at: {payload['generated_at']} by {payload['generated_by']}",
        "-" * 72,
        "1. Overall Test Totals:",
        f"  Total Cases={totals['total_cases']}, Executed={totals['executed_cases']} ({totals['execution_rate']}%)",
        f"  Passed={totals['passed']}, Failed={totals['failed']}, Blocked={totals['blocked']}, Skipped={totals['skipped']}, NotRun={totals['not_run']}",
        f"  Pass Rate={totals['pass_rate']}% (release-scoped, catalogue fallback for unrun cases)",
        f"  Requirement Coverage={totals['requirement_coverage']}% ({totals['covered_requirements']}/{totals['total_requirements']})",
        "",
        "2. Results by Feature / Requirement:",
    ]
    for req in payload.get("feature_results", []):
        tcs = ", ".join(req["test_cases"]) if req["test_cases"] else "None"
        lines.append(
            f"  - {req['id']} ({req['title']}): Cases=[{tcs}] "
            f"P={req['passed']} F={req['failed']} B={req['blocked']} S={req['skipped']} NR={req['not_run']} -> {req['assessment']}"
        )

    lines.append("")
    lines.append("3. Defect Summary:")
    lines.append(
        f"  Total={defect_summary['total']}, Open={defect_summary['open_total']}, "
        f"Closed={defect_summary['closed_total']}, OpenCritical={defect_summary['open_critical']}"
    )
    for d in payload.get("defects", []):
        lines.append(
            f"  - #{d['id']}: {d['title']} [{d['severity']} / {d['status']}] (TC: {d['test_case'] or '-'})"
        )
    if not payload.get("defects"):
        lines.append("  - None")

    lines.append("")
    lines.append("4. Exit Criteria & Release Gate Evaluation:")
    lines.append(
        f"  - Pass Rate: Actual={gate['actual_pass_rate']}% (catalogue) vs Target>={gate['criteria']['min_pass_rate']}% "
        f"({'PASS' if gate['passed_criteria']['pass_rate'] else 'FAIL'})"
    )
    lines.append(
        f"  - Open Critical Defects: Actual={gate['actual_open_critical']} vs Target<={gate['criteria']['max_open_critical']} "
        f"({'PASS' if gate['passed_criteria']['open_critical'] else 'FAIL'})"
    )
    lines.append(
        f"  - Requirement Coverage: Actual={gate['actual_req_coverage']}% vs Target>={gate['criteria']['min_req_coverage']}% "
        f"({'PASS' if gate['passed_criteria']['req_coverage'] else 'FAIL'})"
    )
    if gate.get("waiver"):
        w = gate["waiver"]
        lines.append(f"  - Active Waiver by {w['waived_by']}: {w['reason']}")

    wrapped_lines: list[str] = []
    for raw_line in lines:
        if len(raw_line) <= 95:
            wrapped_lines.append(raw_line)
        else:
            for start in range(0, len(raw_line), 95):
                wrapped_lines.append(raw_line[start : start + 95])

    lines_per_page = 52
    pages = [
        wrapped_lines[i : i + lines_per_page]
        for i in range(0, max(len(wrapped_lines), 1), lines_per_page)
    ]

    page_count = len(pages)
    font_obj_id = 3
    first_page_obj_id = 4

    page_obj_ids = [first_page_obj_id + 2 * i for i in range(page_count)]
    kids_refs = " ".join(f"{pid} 0 R" for pid in page_obj_ids)

    objects: list[bytes] = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        f"2 0 obj\n<< /Type /Pages /Kids [{kids_refs}] /Count {page_count} >>\nendobj\n".encode(
            "latin-1"
        ),
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    for i, page_lines in enumerate(pages):
        page_obj_id = first_page_obj_id + 2 * i
        content_obj_id = page_obj_id + 1
        stream_cmds = ["BT", "/F1 10 Tf", "50 790 Td", "13 TL"]
        for idx, line in enumerate(page_lines):
            escaped = _pdf_escape(line)
            if idx == 0:
                stream_cmds.append(f"({escaped}) Tj")
            else:
                stream_cmds.append(f"T* ({escaped}) Tj")
        stream_cmds.append("ET")
        stream_data = "\n".join(stream_cmds).encode("latin-1")

        objects.append(
            (
                f"{page_obj_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> "
                f"/Contents {content_obj_id} 0 R >>\nendobj\n"
            ).encode("latin-1")
        )
        objects.append(
            f"{content_obj_id} 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode(
                "latin-1"
            )
            + stream_data
            + b"\nendstream\nendobj\n"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1"))
    for off in offsets:
        out.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )
    return bytes(out)


def render_summary_pdf_bytes(html_content: str, payload: dict[str, Any]) -> bytes:
    try:
        weasyprint = importlib.import_module("weasyprint")
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        if isinstance(pdf_bytes, bytes) and pdf_bytes.startswith(b"%PDF-"):
            return pdf_bytes
    except Exception:
        pass
    return _fallback_summary_pdf_bytes(payload)


@router.post("/{release_id}/summary-report/snapshots", status_code=201)
def create_summary_report_snapshot(release_id: int, db: DB, user: SnapshotUser):
    release = get_or_404(db, Release, release_id)
    html_content, payload = build_summary_report_data(db, release, user.username)
    snap = TestSummaryReportSnapshot(
        release_id=release.id,
        release_version=release.version,
        release_status=release.status,
        gate_passed=bool(payload["gate"]["gate_passed"]),
        html_content=html_content,
        payload=payload,
        generated_by=user.username,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snapshot_detail_out(snap)


@router.get("/{release_id}/summary-report/snapshots")
def list_summary_report_snapshots(release_id: int, db: DB):
    get_or_404(db, Release, release_id)
    rows = db.scalars(
        select(TestSummaryReportSnapshot)
        .where(TestSummaryReportSnapshot.release_id == release_id)
        .order_by(TestSummaryReportSnapshot.id)
    )
    return [snapshot_summary_out(s) for s in rows]


@router.get("/{release_id}/summary-report/snapshots/{snapshot_id}")
def get_summary_report_snapshot(release_id: int, snapshot_id: int, db: DB):
    get_or_404(db, Release, release_id)
    snap = db.scalar(
        select(TestSummaryReportSnapshot).where(
            TestSummaryReportSnapshot.id == snapshot_id,
            TestSummaryReportSnapshot.release_id == release_id,
        )
    )
    if snap is None:
        raise HTTPException(404, "Test Summary Report anlık görüntüsü (snapshot) bulunamadı")
    return snapshot_detail_out(snap)


@router.get("/{release_id}/summary-report/export")
def export_summary_report(
    release_id: int,
    db: DB,
    format: Literal["html", "pdf"] = Query("html"),
    snapshot_id: int | None = Query(None),
):
    release = get_or_404(db, Release, release_id)
    if snapshot_id is not None:
        snap = db.scalar(
            select(TestSummaryReportSnapshot).where(
                TestSummaryReportSnapshot.id == snapshot_id,
                TestSummaryReportSnapshot.release_id == release.id,
            )
        )
        if snap is None:
            raise HTTPException(404, "Test Summary Report anlık görüntüsü (snapshot) bulunamadı")
        html_content = snap.html_content
        payload = snap.payload
        export_version = snap.release_version
    else:
        html_content, payload = build_summary_report_data(db, release, "system")
        export_version = release.version

    if format == "pdf":
        pdf_bytes = render_summary_pdf_bytes(html_content, payload)
        safe_version = "".join(
            ch if (ch.isalnum() or ch in ("-", "_", ".")) else "_" for ch in export_version
        ).strip("_") or "0"
        filename = f"test-summary-report-{release.id}-{safe_version}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return HTMLResponse(content=html_content)
