"""IEEE 829 Test Incident Report (defect başına) ve Test Log (koşum başına) üretimi ve snapshot saklama (PLN-39)."""
import importlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .access import require_access, require_defect_access
from .auth import ADMIN, TEST_LEAD, TESTER, CurrentUser, require_roles
from .db import DB
from .models import (
    Defect,
    DefectHistory,
    Project,
    Release,
    TestCase,
    TestExecution,
    TestIncidentReportSnapshot,
    TestLogSnapshot,
    TestRun,
    TestSuite,
    User,
    execution_defects,
)
from .test_plans import _pdf_escape

router = APIRouter(prefix="/api", tags=["test-reports"])
SnapshotUser = Annotated[User, Depends(require_roles(ADMIN, TEST_LEAD, TESTER))]

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "j2"]),
)


def _fmt_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _pdf_from_lines(lines: list[str]) -> bytes:
    """WeasyPrint / GTK bulunmadığında standart uyumlu %PDF-1.4 üretir (RSK-07)."""
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


def _fallback_incident_pdf_bytes(payload: dict[str, Any]) -> bytes:
    defect = payload["defect"]
    tc = payload.get("test_case")
    lines: list[str] = [
        f"IEEE 829 / ISO/IEC/IEEE 29119-3 TEST INCIDENT REPORT: {payload['identifier']}",
        f"Defect #{defect['id']}: {defect['title']}",
        f"Severity: {defect['severity']} | Status: {defect['status']}",
        f"Generated at: {payload['generated_at']} by {payload['generated_by']}",
        "-" * 72,
        "1. Incident Summary:",
        f"  Identifier: {payload['identifier']}",
        f"  Title: {defect['title']}",
        f"  Verification Gate: {payload['verification_summary']}",
        "",
        "2. Linked Test Case Specification:",
    ]
    if tc:
        reqs = ", ".join(tc["requirements"]) if tc["requirements"] else tc["requirement"]
        lines.extend(
            [
                f"  Test Case: {tc['id']} - {tc['title']} (Status: {tc['status']})",
                f"  Priority: {tc['priority']} | Automated: {tc['automated']} | Suite: {tc['suite_name'] or '-'}",
                f"  Requirements: {reqs}",
                f"  Expected Result: {tc['expected_result'] or '-'}",
                "  Steps:",
                *(f"    {idx + 1}. {step}" for idx, step in enumerate(tc["steps"] or [])),
            ]
        )
    else:
        lines.append("  - No directly linked test case.")

    lines.append("")
    lines.append("3. Linked Test Executions:")
    for ex in payload.get("executions", []):
        lines.append(
            f"  - Exec #{ex['id']} (Run #{ex['run_id']} {ex['run_name']}): "
            f"TC={ex['test_case_id']} Status={ex['status']} "
            f"Actual={ex['actual_result'] or '-'} By={ex['executed_by'] or '-'}"
        )
    if not payload.get("executions"):
        lines.append("  - None")

    lines.append("")
    lines.append("4. Immutable Defect History Timeline:")
    for idx, h in enumerate(payload.get("history", []), start=1):
        from_label = h["from_status"] or "(Created)"
        lines.append(f"  {idx}. {from_label} -> {h['to_status']} at {h['at']}")

    return _pdf_from_lines(lines)


def _fallback_test_log_pdf_bytes(payload: dict[str, Any]) -> bytes:
    run = payload["run"]
    project = payload["project"]
    release = payload.get("release")
    suite = payload.get("suite")
    summary = payload["summary"]

    lines: list[str] = [
        f"IEEE 829 / ISO/IEC/IEEE 29119-3 TEST LOG: {payload['identifier']}",
        f"Test Run #{run['id']}: {run['name']}",
        f"Project: {project['name']} | Release: {release['version'] if release else 'Genel'} | Suite: {suite['name'] if suite else 'Genel'}",
        f"Created by: {run['created_by']} at {run['created_at']}",
        f"Generated at: {payload['generated_at']} by {payload['generated_by']}",
        "-" * 72,
        "1. Execution Summary:",
        f"  Total={summary['total']}, Executed={summary['executed']} ({summary['execution_rate']}%), "
        f"Passed={summary['passed']}, Failed={summary['failed']}, Blocked={summary['blocked']}, "
        f"Skipped={summary['skipped']}, NotRun={summary['not_run']}, PassRate={summary['pass_rate']}%",
        "",
        "2. Execution Entries:",
    ]
    for ex in payload.get("executions", []):
        defs = ", ".join(f"#{did}" for did in ex["defect_ids"]) if ex["defect_ids"] else "-"
        lines.append(
            f"  - Exec #{ex['id']} [{ex['test_case_id']}: {ex['test_case_title']}]: "
            f"Status={ex['status']} | Actual={ex['actual_result'] or '-'} | "
            f"Notes={ex['notes'] or '-'} | By={ex['executed_by'] or '-'} ({ex['executed_at'] or 'Not Run'}) | "
            f"Defects={defs}"
        )
    if not payload.get("executions"):
        lines.append("  - None")

    lines.append("")
    lines.append("3. Linked Anomalies & Defects:")
    for d in payload.get("defects", []):
        lines.append(
            f"  - #{d['id']}: {d['title']} [{d['severity']} / {d['status']}] (TC: {d['test_case'] or '-'})"
        )
    if not payload.get("defects"):
        lines.append("  - None")

    return _pdf_from_lines(lines)


def _render_pdf(html_content: str, fallback_fn, payload: dict[str, Any]) -> bytes:
    try:
        weasyprint = importlib.import_module("weasyprint")
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        if isinstance(pdf_bytes, bytes) and pdf_bytes.startswith(b"%PDF-"):
            return pdf_bytes
    except Exception:
        pass
    return fallback_fn(payload)


# --- Test Incident Report (Defect başına, IEEE 829 / 29119-3) ----------------
def get_defect_or_404(db: Session, defect_id: int) -> Defect:
    defect = db.get(Defect, defect_id)
    if defect is None:
        raise HTTPException(404, "Defect bulunamadı")
    return defect


def incident_snapshot_summary_out(s: TestIncidentReportSnapshot) -> dict[str, Any]:
    return {
        "id": s.id,
        "defect_id": s.defect_id,
        "status": s.status,
        "severity": s.severity,
        "generated_by": s.generated_by,
        "generated_at": s.generated_at,
    }


def incident_snapshot_detail_out(s: TestIncidentReportSnapshot) -> dict[str, Any]:
    return {
        **incident_snapshot_summary_out(s),
        "html_content": s.html_content,
        "payload": s.payload,
    }


def build_incident_report_data(
    db: Session, defect: Defect, generated_by: str
) -> tuple[str, dict[str, Any]]:
    tc_dict: dict[str, Any] | None = None
    req_dicts: list[dict[str, Any]] = []
    if defect.test_case is not None:
        tc = db.scalar(
            select(TestCase)
            .options(selectinload(TestCase.requirements), selectinload(TestCase.suite))
            .where(TestCase.id == defect.test_case)
        )
        if tc is not None:
            reqs_sorted = sorted(tc.requirements, key=lambda r: r.id)
            tc_dict = {
                "id": tc.id,
                "title": tc.title,
                "suite_id": tc.suite_id,
                "suite_name": tc.suite.name if tc.suite is not None else None,
                "requirement": tc.requirement,
                "requirements": [r.id for r in reqs_sorted],
                "status": tc.status,
                "priority": tc.priority,
                "automated": tc.automated,
                "steps": list(tc.steps or []),
                "expected_result": tc.expected_result,
            }
            req_dicts = [
                {"id": r.id, "title": r.title, "description": r.description} for r in reqs_sorted
            ]

    exec_rows = list(
        db.scalars(
            select(TestExecution)
            .join(execution_defects, execution_defects.c.execution_id == TestExecution.id)
            .options(selectinload(TestExecution.run))
            .where(execution_defects.c.defect_id == defect.id)
            .order_by(TestExecution.id)
        )
    )
    exec_dicts = [
        {
            "id": ex.id,
            "run_id": ex.run_id,
            "run_name": ex.run.name if ex.run is not None else f"Run #{ex.run_id}",
            "test_case_id": ex.test_case_id,
            "status": ex.status,
            "actual_result": ex.actual_result,
            "notes": ex.notes,
            "executed_by": ex.executed_by,
            "executed_at": _fmt_dt(ex.executed_at),
        }
        for ex in exec_rows
    ]

    history_rows = list(
        db.scalars(
            select(DefectHistory)
            .where(DefectHistory.defect_id == defect.id)
            .order_by(DefectHistory.id)
        )
    )
    history_dicts = [
        {
            "id": h.id,
            "from_status": h.from_status,
            "to_status": h.to_status,
            "at": _fmt_dt(h.at) or "",
        }
        for h in history_rows
    ]

    linked_case_ids: set[str] = {str(ex["test_case_id"]) for ex in exec_dicts}
    if defect.test_case:
        linked_case_ids.add(defect.test_case)

    if not linked_case_ids:
        verification_summary = "Doğrudan bağlı test vakası bulunmuyor."
    else:
        all_passed = True
        for case_id in sorted(linked_case_ids):
            latest_ex = db.scalar(
                select(TestExecution)
                .where(TestExecution.test_case_id == case_id)
                .order_by(TestExecution.executed_at.desc().nulls_last(), TestExecution.id.desc())
                .limit(1)
            )
            if latest_ex is not None:
                if latest_ex.status != "Passed":
                    all_passed = False
            else:
                case_row = db.get(TestCase, case_id)
                if case_row is None or case_row.status != "Passed":
                    all_passed = False
        verification_summary = (
            "Son doğrulama yürütmesi Passed (Kapanış şartı sağlandı)."
            if all_passed
            else "Son doğrulama yürütmesi henüz Passed değil (Resolved -> Closed engelli)."
        )

    generated_at_iso = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    identifier = f"TIR-DEF-{defect.id:04d}"
    payload: dict[str, Any] = {
        "identifier": identifier,
        "generated_by": generated_by,
        "generated_at": generated_at_iso,
        "defect": {
            "id": defect.id,
            "title": defect.title,
            "severity": defect.severity,
            "status": defect.status,
            "test_case": defect.test_case,
        },
        "test_case": tc_dict,
        "requirements": req_dicts,
        "executions": exec_dicts,
        "history": history_dicts,
        "verification_summary": verification_summary,
    }
    template = jinja_env.get_template("test_incident_report.html.j2")
    html_content = template.render(**payload)
    return html_content, payload


@router.post("/defects/{defect_id}/incident-report/snapshots", status_code=201)
def create_incident_report_snapshot(defect_id: int, db: DB, user: SnapshotUser):
    defect = get_defect_or_404(db, defect_id)
    require_defect_access(db, user, defect)
    html_content, payload = build_incident_report_data(db, defect, user.username)
    snap = TestIncidentReportSnapshot(
        defect_id=defect.id,
        status=defect.status,
        severity=defect.severity,
        html_content=html_content,
        payload=payload,
        generated_by=user.username,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return incident_snapshot_detail_out(snap)


@router.get("/defects/{defect_id}/incident-report/snapshots")
def list_incident_report_snapshots(defect_id: int, db: DB, user: CurrentUser):
    require_defect_access(db, user, get_defect_or_404(db, defect_id))
    rows = db.scalars(
        select(TestIncidentReportSnapshot)
        .where(TestIncidentReportSnapshot.defect_id == defect_id)
        .order_by(TestIncidentReportSnapshot.id)
    )
    return [incident_snapshot_summary_out(s) for s in rows]


@router.get("/defects/{defect_id}/incident-report/snapshots/{snapshot_id}")
def get_incident_report_snapshot(defect_id: int, snapshot_id: int, db: DB, user: CurrentUser):
    require_defect_access(db, user, get_defect_or_404(db, defect_id))
    snap = db.scalar(
        select(TestIncidentReportSnapshot).where(
            TestIncidentReportSnapshot.id == snapshot_id,
            TestIncidentReportSnapshot.defect_id == defect_id,
        )
    )
    if snap is None:
        raise HTTPException(404, "Test Incident Report anlık görüntüsü (snapshot) bulunamadı")
    return incident_snapshot_detail_out(snap)


@router.get("/defects/{defect_id}/incident-report/export")
def export_incident_report(
    defect_id: int,
    db: DB,
    user: CurrentUser,
    format: Literal["html", "pdf"] = Query("html"),
    snapshot_id: int | None = Query(None),
):
    defect = get_defect_or_404(db, defect_id)
    require_defect_access(db, user, defect)
    if snapshot_id is not None:
        snap = db.scalar(
            select(TestIncidentReportSnapshot).where(
                TestIncidentReportSnapshot.id == snapshot_id,
                TestIncidentReportSnapshot.defect_id == defect.id,
            )
        )
        if snap is None:
            raise HTTPException(404, "Test Incident Report anlık görüntüsü (snapshot) bulunamadı")
        html_content = snap.html_content
        payload = snap.payload
    else:
        html_content, payload = build_incident_report_data(db, defect, "system")

    if format == "pdf":
        pdf_bytes = _render_pdf(html_content, _fallback_incident_pdf_bytes, payload)
        suffix = f"-snap-{snapshot_id}" if snapshot_id is not None else ""
        filename = f"test-incident-report-{defect.id}{suffix}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return HTMLResponse(content=html_content)


# --- Test Log (Test Koşumu başına, IEEE 829 / 29119-3) -----------------------
def get_run_for_log_or_404(db: Session, run_id: int) -> TestRun:
    run = db.scalar(
        select(TestRun)
        .options(selectinload(TestRun.executions).selectinload(TestExecution.defects))
        .where(TestRun.id == run_id)
    )
    if run is None:
        raise HTTPException(404, "TestRun bulunamadı")
    return run


def test_log_snapshot_summary_out(s: TestLogSnapshot) -> dict[str, Any]:
    return {
        "id": s.id,
        "test_run_id": s.test_run_id,
        "generated_by": s.generated_by,
        "generated_at": s.generated_at,
    }


def test_log_snapshot_detail_out(s: TestLogSnapshot) -> dict[str, Any]:
    return {
        **test_log_snapshot_summary_out(s),
        "html_content": s.html_content,
        "payload": s.payload,
    }


def build_test_log_data(
    db: Session, run: TestRun, generated_by: str
) -> tuple[str, dict[str, Any]]:
    project = db.get(Project, run.project_id)
    assert project is not None
    release = db.get(Release, run.release_id) if run.release_id is not None else None
    suite = db.get(TestSuite, run.suite_id) if run.suite_id is not None else None

    case_ids = [ex.test_case_id for ex in run.executions]
    cases_by_id: dict[str, TestCase] = {}
    if case_ids:
        for tc in db.scalars(
            select(TestCase)
            .options(selectinload(TestCase.requirements))
            .where(TestCase.id.in_(case_ids))
        ):
            cases_by_id[tc.id] = tc

    exec_dicts: list[dict[str, Any]] = []
    defects_by_id: dict[int, Defect] = {}
    counts = {"Passed": 0, "Failed": 0, "Blocked": 0, "Skipped": 0, "Not Run": 0}

    for ex in run.executions:
        counts[ex.status] = counts.get(ex.status, 0) + 1
        tc_row = cases_by_id.get(ex.test_case_id)
        for d in ex.defects:
            defects_by_id[d.id] = d
        exec_dicts.append(
            {
                "id": ex.id,
                "test_case_id": ex.test_case_id,
                "test_case_title": tc_row.title if tc_row is not None else ex.test_case_id,
                "expected_result": tc_row.expected_result if tc_row is not None else "",
                "requirements": sorted(r.id for r in tc_row.requirements) if tc_row is not None else [],
                "status": ex.status,
                "actual_result": ex.actual_result,
                "notes": ex.notes,
                "executed_by": ex.executed_by,
                "executed_at": _fmt_dt(ex.executed_at),
                "defect_ids": [d.id for d in ex.defects],
            }
        )

    total = len(exec_dicts)
    executed = total - counts["Not Run"]
    decisive = counts["Passed"] + counts["Failed"]
    summary = {
        "total": total,
        "executed": executed,
        "passed": counts["Passed"],
        "failed": counts["Failed"],
        "blocked": counts["Blocked"],
        "skipped": counts["Skipped"],
        "not_run": counts["Not Run"],
        "execution_rate": round(executed / total * 100, 1) if total else 0.0,
        "pass_rate": round(counts["Passed"] / decisive * 100, 1) if decisive else 0.0,
    }

    defect_dicts = [
        {
            "id": d.id,
            "title": d.title,
            "severity": d.severity,
            "status": d.status,
            "test_case": d.test_case,
        }
        for d in sorted(defects_by_id.values(), key=lambda item: item.id)
    ]

    generated_at_iso = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    identifier = f"TL-RUN-{run.id:04d}"
    payload: dict[str, Any] = {
        "identifier": identifier,
        "generated_by": generated_by,
        "generated_at": generated_at_iso,
        "project": {"id": project.id, "name": project.name, "description": project.description},
        "release": {"id": release.id, "version": release.version} if release is not None else None,
        "suite": {"id": suite.id, "name": suite.name} if suite is not None else None,
        "run": {
            "id": run.id,
            "name": run.name,
            "created_by": run.created_by,
            "created_at": _fmt_dt(run.created_at) or "",
        },
        "summary": summary,
        "executions": exec_dicts,
        "defects": defect_dicts,
    }
    template = jinja_env.get_template("test_log.html.j2")
    html_content = template.render(**payload)
    return html_content, payload


@router.post("/test-runs/{run_id}/test-log/snapshots", status_code=201)
def create_test_log_snapshot(run_id: int, db: DB, user: SnapshotUser):
    run = get_run_for_log_or_404(db, run_id)
    require_access(db, user, [run.project_id])
    html_content, payload = build_test_log_data(db, run, user.username)
    snap = TestLogSnapshot(
        test_run_id=run.id,
        html_content=html_content,
        payload=payload,
        generated_by=user.username,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return test_log_snapshot_detail_out(snap)


@router.get("/test-runs/{run_id}/test-log/snapshots")
def list_test_log_snapshots(run_id: int, db: DB, user: CurrentUser):
    require_access(db, user, [get_run_for_log_or_404(db, run_id).project_id])
    rows = db.scalars(
        select(TestLogSnapshot)
        .where(TestLogSnapshot.test_run_id == run_id)
        .order_by(TestLogSnapshot.id)
    )
    return [test_log_snapshot_summary_out(s) for s in rows]


@router.get("/test-runs/{run_id}/test-log/snapshots/{snapshot_id}")
def get_test_log_snapshot(run_id: int, snapshot_id: int, db: DB, user: CurrentUser):
    require_access(db, user, [get_run_for_log_or_404(db, run_id).project_id])
    snap = db.scalar(
        select(TestLogSnapshot).where(
            TestLogSnapshot.id == snapshot_id,
            TestLogSnapshot.test_run_id == run_id,
        )
    )
    if snap is None:
        raise HTTPException(404, "Test Log anlık görüntüsü (snapshot) bulunamadı")
    return test_log_snapshot_detail_out(snap)


@router.get("/test-runs/{run_id}/test-log/export")
def export_test_log(
    run_id: int,
    db: DB,
    user: CurrentUser,
    format: Literal["html", "pdf"] = Query("html"),
    snapshot_id: int | None = Query(None),
):
    run = get_run_for_log_or_404(db, run_id)
    require_access(db, user, [run.project_id])
    if snapshot_id is not None:
        snap = db.scalar(
            select(TestLogSnapshot).where(
                TestLogSnapshot.id == snapshot_id,
                TestLogSnapshot.test_run_id == run.id,
            )
        )
        if snap is None:
            raise HTTPException(404, "Test Log anlık görüntüsü (snapshot) bulunamadı")
        html_content = snap.html_content
        payload = snap.payload
    else:
        html_content, payload = build_test_log_data(db, run, run.created_by)

    if format == "pdf":
        pdf_bytes = _render_pdf(html_content, _fallback_test_log_pdf_bytes, payload)
        suffix = f"-snap-{snapshot_id}" if snapshot_id is not None else ""
        filename = f"test-log-{run.id}{suffix}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return HTMLResponse(content=html_content)
