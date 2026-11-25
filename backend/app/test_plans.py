"""IEEE 829 Test Plan yönetimi, anlık görüntü (snapshot) saklama ve HTML/PDF üretimi (PLN-26)."""
import importlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, StringConstraints
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .access import allowed_projects, require_access, scoped
from .auth import ADMIN, TEST_LEAD, TESTER, CurrentUser, require_roles
from .db import DB
from .models import (
    Defect,
    Project,
    Release,
    Requirement,
    TestCase,
    TestExecution,
    TestPlan,
    TestPlanSnapshot,
    TestRun,
    TestSuite,
    User,
    execution_defects,
)

router = APIRouter(prefix="/api/test-plans", tags=["test-plans"])
WRITE = [Depends(require_roles(ADMIN, TEST_LEAD))]
SNAPSHOT = [Depends(require_roles(ADMIN, TEST_LEAD, TESTER))]

PlanStatus = Literal["Draft", "In Review", "Approved"]
VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "Draft": {"In Review"},
    "In Review": {"Draft", "Approved"},
    "Approved": {"Draft"},
}

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "j2"]),
)

TitleStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
VersionStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
SectionStr = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class TestPlanIn(BaseModel):
    project_id: int
    release_id: int | None = None
    version: VersionStr
    title: TitleStr
    scope: SectionStr = ""
    approach: SectionStr = ""
    pass_fail_criteria: SectionStr = ""
    environment: SectionStr = ""
    schedule_risks: SectionStr = ""


class TestPlanStatusIn(BaseModel):
    status: PlanStatus


def get_plan_or_404(db: Session, plan_id: int) -> TestPlan:
    plan = db.scalar(
        select(TestPlan)
        .options(selectinload(TestPlan.snapshots))
        .where(TestPlan.id == plan_id)
    )
    if plan is None:
        raise HTTPException(404, "Test Plan bulunamadı")
    return plan


def get_visible_plan(db: Session, user: User, plan_id: int) -> TestPlan:
    plan = get_plan_or_404(db, plan_id)
    require_access(db, user, [plan.project_id])
    return plan


def validate_project_and_release(db: Session, project_id: int, release_id: int | None) -> None:
    if db.get(Project, project_id) is None:
        raise HTTPException(422, "Proje bulunamadı")
    if release_id is not None:
        release = db.get(Release, release_id)
        if release is None or release.project_id != project_id:
            raise HTTPException(422, "Sürüm bulunamadı veya bu projeye ait değil")


def snapshot_summary_out(s: TestPlanSnapshot) -> dict[str, Any]:
    return {
        "id": s.id,
        "test_plan_id": s.test_plan_id,
        "version": s.version,
        "status": s.status,
        "generated_by": s.generated_by,
        "generated_at": s.generated_at,
    }


def snapshot_detail_out(s: TestPlanSnapshot) -> dict[str, Any]:
    return {
        **snapshot_summary_out(s),
        "html_content": s.html_content,
        "payload": s.payload,
    }


def plan_out(plan: TestPlan, include_snapshots: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": plan.id,
        "project_id": plan.project_id,
        "release_id": plan.release_id,
        "version": plan.version,
        "title": plan.title,
        "status": plan.status,
        "scope": plan.scope,
        "approach": plan.approach,
        "pass_fail_criteria": plan.pass_fail_criteria,
        "environment": plan.environment,
        "schedule_risks": plan.schedule_risks,
        "created_by": plan.created_by,
        "created_at": plan.created_at,
        "snapshot_count": len(plan.snapshots),
    }
    if include_snapshots:
        data["snapshots"] = [snapshot_summary_out(s) for s in plan.snapshots]
    return data


def build_plan_snapshot_data(
    db: Session, plan: TestPlan, generated_by: str
) -> tuple[str, dict[str, Any]]:
    project = db.get(Project, plan.project_id)
    if project is None:
        raise HTTPException(404, "Proje bulunamadı")
    release = db.get(Release, plan.release_id) if plan.release_id is not None else None

    reqs = list(
        db.scalars(
            select(Requirement)
            .options(selectinload(Requirement.test_cases))
            .where(Requirement.project_id == plan.project_id)
            .order_by(Requirement.id)
        )
    )
    req_dicts = [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "test_cases": sorted(t.id for t in r.test_cases),
        }
        for r in reqs
    ]

    project_case_filter = or_(
        TestCase.requirements.any(Requirement.project_id == plan.project_id),
        TestCase.suite.has(TestSuite.project_id == plan.project_id),
    )
    tcs = list(
        db.scalars(
            select(TestCase)
            .where(project_case_filter)
            .options(selectinload(TestCase.requirements))
            .order_by(TestCase.id)
        )
    )
    tc_dicts = [
        {
            "id": t.id,
            "title": t.title,
            "requirement": t.requirement,
            "requirements": sorted(r.id for r in t.requirements),
            "status": t.status,
        }
        for t in tcs
    ]

    other_project_case_ids = select(TestCase.id).where(
        ~project_case_filter,
        or_(
            TestCase.requirements.any(Requirement.project_id != plan.project_id),
            TestCase.suite.has(TestSuite.project_id != plan.project_id),
        ),
    )
    other_project_exec_defect_ids = (
        select(execution_defects.c.defect_id)
        .join(TestExecution, TestExecution.id == execution_defects.c.execution_id)
        .join(TestRun, TestRun.id == TestExecution.run_id)
        .where(TestRun.project_id != plan.project_id)
    )
    project_exec_defect_ids = (
        select(execution_defects.c.defect_id)
        .join(TestExecution, TestExecution.id == execution_defects.c.execution_id)
        .join(TestRun, TestRun.id == TestExecution.run_id)
        .where(TestRun.project_id == plan.project_id)
    )
    defect_branches: list[Any] = [
        Defect.test_case.in_(select(TestCase.id).where(project_case_filter)),
        Defect.id.in_(project_exec_defect_ids),
    ]
    if plan.project_id == 1:
        defect_branches.append(
            Defect.test_case.is_(None) & ~Defect.id.in_(other_project_exec_defect_ids)
        )
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

    total = len(tc_dicts)
    executed = sum(t["status"] in ("Passed", "Failed") for t in tc_dicts)
    passed = sum(t["status"] == "Passed" for t in tc_dicts)
    open_defects = int(
        db.scalar(
            select(func.count()).where(
                Defect.status != "Closed",
                project_defect_filter,
            )
        )
        or 0
    )
    metrics_dict = {
        "total_tests": total,
        "execution_rate": round(executed / total * 100, 1) if total else 0.0,
        "pass_rate": round(passed / executed * 100, 1) if executed else 0.0,
        "open_defects": open_defects,
    }

    generated_at_iso = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    identifier = f"TP-{project.name}-{plan.version}"
    plan_meta = {
        "id": plan.id,
        "identifier": identifier,
        "version": plan.version,
        "title": plan.title,
        "status": plan.status,
        "scope": plan.scope,
        "approach": plan.approach,
        "pass_fail_criteria": plan.pass_fail_criteria,
        "environment": plan.environment,
        "schedule_risks": plan.schedule_risks,
        "created_by": plan.created_by,
    }
    project_meta = {"id": project.id, "name": project.name, "description": project.description}
    release_meta = (
        {"id": release.id, "version": release.version} if release is not None else None
    )

    payload: dict[str, Any] = {
        "identifier": identifier,
        "generated_by": generated_by,
        "generated_at": generated_at_iso,
        "project": project_meta,
        "release": release_meta,
        "plan": plan_meta,
        "requirements": req_dicts,
        "test_cases": tc_dicts,
        "defects": defect_dicts,
        "metrics": metrics_dict,
    }

    template = jinja_env.get_template("test_plan.html.j2")
    html_content = template.render(**payload)
    return html_content, payload


_TR_ASCII = str.maketrans(
    {
        "ç": "c",
        "Ç": "C",
        "ğ": "g",
        "Ğ": "G",
        "ı": "i",
        "İ": "I",
        "ö": "o",
        "Ö": "O",
        "ş": "s",
        "Ş": "S",
        "ü": "u",
        "Ü": "U",
        "–": "-",
        "—": "-",
        "·": "-",
    }
)


def _pdf_escape(text: str) -> str:
    ascii_text = text.translate(_TR_ASCII).encode("latin-1", errors="replace").decode("latin-1")
    return ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _fallback_pdf_bytes(payload: dict[str, Any]) -> bytes:
    """RSK-07 fallback: WeasyPrint / GTK bulunmadığında standart uyumlu %PDF-1.4 üretir."""
    plan = payload["plan"]
    project = payload["project"]
    release = payload.get("release")
    metrics = payload["metrics"]

    lines: list[str] = [
        f"IEEE 829 / ISO/IEC/IEEE 29119-3 TEST PLAN: {payload['identifier']}",
        f"Title: {plan['title']}",
        f"Project: {project['name']} | Release: {release['version'] if release else 'Genel'}",
        f"Version: {plan['version']} | Status: {plan['status']} | Created by: {plan['created_by']}",
        f"Generated at: {payload['generated_at']} by {payload['generated_by']}",
        "-" * 72,
        "1. Scope (Test Items & Features):",
        *(plan["scope"].splitlines() or ["Belirtilmedi."]),
        "",
        "2. Test Approach:",
        *(plan["approach"].splitlines() or ["Belirtilmedi."]),
        "",
        "3. Pass/Fail & Entry/Exit Criteria:",
        *(plan["pass_fail_criteria"].splitlines() or ["Belirtilmedi."]),
        "",
        "4. Test Environment & Deliverables:",
        *(plan["environment"].splitlines() or ["Belirtilmedi."]),
        "",
        "5. Schedule, Responsibilities & Risks:",
        *(plan["schedule_risks"].splitlines() or ["Belirtilmedi."]),
        "",
        "6. Requirements Traceability:",
    ]
    for r in payload.get("requirements", []):
        tcs = ", ".join(r["test_cases"]) if r["test_cases"] else "None"
        lines.append(f"  - {r['id']}: {r['title']} -> [{tcs}]")

    lines.append("")
    lines.append("7. Test Cases:")
    for tc in payload.get("test_cases", []):
        lines.append(f"  - {tc['id']}: {tc['title']} ({tc['status']}) [Req: {tc['requirement']}]")

    lines.append("")
    lines.append("8. Defects:")
    for d in payload.get("defects", []):
        tc_ref = d["test_case"] or "-"
        lines.append(
            f"  - #{d['id']}: {d['title']} [{d['severity']} / {d['status']}] (TC: {tc_ref})"
        )
    if not payload.get("defects"):
        lines.append("  - None")

    lines.append("")
    lines.append(
        f"9. Metrics Summary: Total={metrics['total_tests']}, "
        f"Exec={metrics['execution_rate']}%, Pass={metrics['pass_rate']}%, "
        f"OpenDefects={metrics['open_defects']}"
    )

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


def render_pdf_bytes(html_content: str, payload: dict[str, Any]) -> bytes:
    try:
        weasyprint = importlib.import_module("weasyprint")
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        if isinstance(pdf_bytes, bytes) and pdf_bytes.startswith(b"%PDF-"):
            return pdf_bytes
    except Exception:
        return _fallback_pdf_bytes(payload)
    return _fallback_pdf_bytes(payload)


# --- Uç Noktalar --------------------------------------------------------------
@router.get("")
def list_test_plans(db: DB, user: CurrentUser):
    stmt = select(TestPlan).options(selectinload(TestPlan.snapshots)).order_by(TestPlan.id)
    rows = db.scalars(scoped(stmt, TestPlan.project_id, allowed_projects(db, user)))
    return [plan_out(p, include_snapshots=False) for p in rows]


@router.post("", status_code=201)
def create_test_plan(
    body: TestPlanIn,
    db: DB,
    user: Annotated[User, Depends(require_roles(ADMIN, TEST_LEAD))],
):
    validate_project_and_release(db, body.project_id, body.release_id)
    plan = TestPlan(status="Draft", created_by=user.username, **body.model_dump())
    db.add(plan)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Bu projede aynı sürüm numaralı bir Test Plan zaten var") from None
    return plan_out(get_plan_or_404(db, plan.id), include_snapshots=True)


@router.get("/{plan_id}")
def get_test_plan(plan_id: int, db: DB, user: CurrentUser):
    return plan_out(get_visible_plan(db, user, plan_id), include_snapshots=True)


@router.put("/{plan_id}", dependencies=WRITE)
def update_test_plan(plan_id: int, body: TestPlanIn, db: DB):
    plan = get_plan_or_404(db, plan_id)
    if plan.status == "Approved":
        raise HTTPException(409, "Onaylanmış (Approved) Test Plan düzenlenemez; önce Draft durumuna alın")
    validate_project_and_release(db, body.project_id, body.release_id)
    for field, value in body.model_dump().items():
        setattr(plan, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Bu projede aynı sürüm numaralı bir Test Plan zaten var") from None
    return plan_out(get_plan_or_404(db, plan.id), include_snapshots=True)


@router.put("/{plan_id}/status", dependencies=WRITE)
def update_test_plan_status(plan_id: int, body: TestPlanStatusIn, db: DB):
    plan = get_plan_or_404(db, plan_id)
    if body.status == plan.status:
        return plan_out(plan, include_snapshots=True)
    allowed = VALID_STATUS_TRANSITIONS.get(plan.status, set())
    if body.status not in allowed:
        raise HTTPException(
            409,
            f"Geçersiz Test Plan durum geçişi: {plan.status} -> {body.status}. "
            "Test Plan doğrudan Approved yapılamaz; önce In Review durumuna geçirilmelidir.",
        )
    plan.status = body.status
    db.commit()
    return plan_out(get_plan_or_404(db, plan.id), include_snapshots=True)


@router.delete("/{plan_id}", status_code=204, dependencies=WRITE)
def delete_test_plan(plan_id: int, db: DB):
    plan = get_plan_or_404(db, plan_id)
    if plan.status == "Approved":
        raise HTTPException(409, "Onaylanmış (Approved) Test Plan silinemez")
    db.delete(plan)
    db.commit()


@router.post("/{plan_id}/snapshots", status_code=201)
def create_test_plan_snapshot(
    plan_id: int,
    db: DB,
    user: Annotated[User, Depends(require_roles(ADMIN, TEST_LEAD, TESTER))],
):
    plan = get_visible_plan(db, user, plan_id)
    html_content, payload = build_plan_snapshot_data(db, plan, user.username)
    snap = TestPlanSnapshot(
        test_plan_id=plan.id,
        version=plan.version,
        status=plan.status,
        html_content=html_content,
        payload=payload,
        generated_by=user.username,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snapshot_detail_out(snap)


@router.get("/{plan_id}/snapshots")
def list_test_plan_snapshots(plan_id: int, db: DB, user: CurrentUser):
    plan = get_visible_plan(db, user, plan_id)
    return [snapshot_summary_out(s) for s in plan.snapshots]


@router.get("/{plan_id}/snapshots/{snapshot_id}")
def get_test_plan_snapshot(plan_id: int, snapshot_id: int, db: DB, user: CurrentUser):
    plan = get_visible_plan(db, user, plan_id)
    snap = db.scalar(
        select(TestPlanSnapshot).where(
            TestPlanSnapshot.id == snapshot_id,
            TestPlanSnapshot.test_plan_id == plan.id,
        )
    )
    if snap is None:
        raise HTTPException(404, "Test Plan anlık görüntüsü (snapshot) bulunamadı")
    return snapshot_detail_out(snap)


@router.get("/{plan_id}/export")
def export_test_plan(
    plan_id: int,
    db: DB,
    user: CurrentUser,
    format: Literal["html", "pdf"] = Query("html"),
    snapshot_id: int | None = Query(None),
):
    plan = get_visible_plan(db, user, plan_id)
    if snapshot_id is not None:
        snap = db.scalar(
            select(TestPlanSnapshot).where(
                TestPlanSnapshot.id == snapshot_id,
                TestPlanSnapshot.test_plan_id == plan.id,
            )
        )
        if snap is None:
            raise HTTPException(404, "Test Plan anlık görüntüsü (snapshot) bulunamadı")
        html_content = snap.html_content
        payload = snap.payload
        export_version = snap.version
    else:
        html_content, payload = build_plan_snapshot_data(db, plan, plan.created_by)
        export_version = plan.version

    if format == "pdf":
        pdf_bytes = render_pdf_bytes(html_content, payload)
        safe_version = "".join(
            ch if (ch.isalnum() or ch in ("-", "_", ".")) else "_" for ch in export_version
        ).strip("_") or "0"
        filename = f"test-plan-{plan.id}-{safe_version}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return HTMLResponse(content=html_content)
