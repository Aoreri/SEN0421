"""PLN-24/R5: SQL aggregates over scoped runs, links and immutable history."""
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import Float, case, cast, func, or_, select, union_all
from sqlalchemy.orm import Session

from .db import DB
from .models import (
    Defect,
    DefectHistory,
    Project,
    Release,
    Requirement,
    TestExecution,
    TestRun,
    execution_defects,
    test_case_requirements,
)
from .projects import get_or_404

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])
STATUSES = ("Passed", "Failed", "Blocked", "Skipped", "Not Run")


def percent(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0


def utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise HTTPException(422, "Metric timestamps must include a timezone")
    return value.astimezone(UTC) if value is not None else None


def hours_between(db: Session, end, start):
    if db.get_bind().dialect.name == "postgresql":
        return func.extract("epoch", end - start) / 3600.0
    return (func.julianday(end) - func.julianday(start)) * 24.0


def event_day(db: Session, timestamp):
    return func.date(func.timezone("UTC", timestamp)) if db.get_bind().dialect.name == "postgresql" else func.date(timestamp)


@router.get("/expanded")
def expanded_metrics(db: DB,
                     project_id: Annotated[int | None, Query(ge=1)] = None,
                     release_id: Annotated[int | None, Query(ge=1)] = None,
                     start_at: datetime | None = None, end_at: datetime | None = None,
                     sprint_id: str | None = None):
    if sprint_id is not None:
        raise HTTPException(422, "Sprint model is not available; use start_at/end_at for a sprint window")
    start, end = utc(start_at), utc(end_at)
    if start is not None and end is not None and start >= end:
        raise HTTPException(422, "start_at must precede end_at")
    if release_id is not None:
        release = get_or_404(db, Release, release_id)
        if project_id is not None and project_id != release.project_id:
            raise HTTPException(422, "Release belongs to another project")
        project_id = release.project_id
    if project_id is not None:
        get_or_404(db, Project, project_id)
    as_of = min(datetime.now(UTC), end) if end is not None else datetime.now(UTC)
    run_query = select(TestRun.id, TestRun.name, TestRun.created_at).where(TestRun.created_at <= as_of)
    if project_id is not None:
        run_query = run_query.where(TestRun.project_id == project_id)
    if release_id is not None:
        run_query = run_query.where(TestRun.release_id == release_id)
    if start is not None:
        run_query = run_query.where(TestRun.created_at >= start)
    if end is not None:
        run_query = run_query.where(TestRun.created_at < end)
    runs = run_query.cte("scoped_runs")
    # Read current execution snapshots, not a fabricated execution audit trail.
    counts = select(runs.c.id.label("run_id"), runs.c.name.label("run_name"),
                    runs.c.created_at.label("executed_at"),
                    *[func.sum(case((TestExecution.status == status, 1), else_=0)).label(
                        status.lower().replace(" ", "_")) for status in STATUSES]
                    ).select_from(runs.outerjoin(TestExecution, TestExecution.run_id == runs.c.id))\
                     .group_by(runs.c.id, runs.c.name, runs.c.created_at).cte("run_counts")
    totals = db.execute(select(*[func.coalesce(func.sum(counts.c[status.lower().replace(" ", "_")]), 0)
                                  .label(status.lower().replace(" ", "_")) for status in STATUSES])).one()
    total = sum(totals)
    run_count = db.scalar(select(func.count()).select_from(runs)) or 0
    series = []
    for row in db.execute(select(counts).order_by(counts.c.executed_at.desc(), counts.c.run_id.desc())
                          .limit(1000)).mappings():
        point = dict(row)
        point["pass_rate"] = percent(point["passed"], point["passed"] + point["failed"])
        series.append(point)
    series.reverse()

    req_scope = select(Requirement.id)
    if project_id is not None:
        req_scope = req_scope.where(Requirement.project_id == project_id)
    reqs = req_scope.cte("scoped_requirements")
    req_total = db.scalar(select(func.count()).select_from(reqs)) or 0
    covered_req = db.scalar(select(func.count()).select_from(reqs).where(
        select(test_case_requirements.c.test_case_id)
        .where(test_case_requirements.c.requirement_id == reqs.c.id).exists())) or 0

    # Release membership is evidenced by explicit execution↔defect links.
    # A case belonging to the same project does not prove release membership.
    defects_query = select(Defect.id, Defect.severity)
    if release_id is not None:
        linked_defects = select(execution_defects.c.defect_id).join(
            TestExecution, TestExecution.id == execution_defects.c.execution_id).join(
            TestRun, TestRun.id == TestExecution.run_id).where(TestRun.release_id == release_id)
        defects_query = defects_query.where(Defect.id.in_(linked_defects))
    elif project_id is not None:
        linked_cases = select(test_case_requirements.c.test_case_id).join(
            Requirement, Requirement.id == test_case_requirements.c.requirement_id).where(
            Requirement.project_id == project_id)
        linked_defects = select(execution_defects.c.defect_id).join(
            TestExecution, TestExecution.id == execution_defects.c.execution_id).join(
            TestRun, TestRun.id == TestExecution.run_id).where(TestRun.project_id == project_id)
        defects_query = defects_query.where(or_(Defect.test_case.in_(linked_cases),
                                                Defect.id.in_(linked_defects)))
    scoped_defects = defects_query.cte("scoped_defects")
    h = DefectHistory
    events_query = select(h).where(h.at <= as_of)
    if end is not None:
        events_query = events_query.where(h.at < end)
    events = events_query.cte("history_to_as_of")
    e = events.c
    first = select(e.defect_id,
        func.min(case((e.from_status.is_(None) & (e.to_status == "Open"), e.at))).label("opened"),
        func.min(case((e.to_status == "Resolved", e.at))).label("resolved"),
        func.min(case((e.to_status == "Closed", e.at))).label("closed"),
        func.max(case((e.from_status.in_(["Resolved", "Closed"]) & (e.to_status == "Open"), 1),
                      else_=0)).label("reopened"),
    ).group_by(e.defect_id).cte("first_events")
    latest = select(e.defect_id, e.to_status,
                    func.row_number().over(partition_by=e.defect_id,
                                           order_by=(e.at.desc(), e.id.desc())).label("rank"))\
                    .cte("latest_event")
    missing_creation = db.scalar(select(func.count()).select_from(scoped_defects.outerjoin(
        first, first.c.defect_id == scoped_defects.c.id)).where(first.c.opened.is_(None))) or 0
    cohort_query = select(scoped_defects.c.id, scoped_defects.c.severity, first.c.opened,
        first.c.resolved, first.c.closed, first.c.reopened, latest.c.to_status.label("status"))\
        .join(first, first.c.defect_id == scoped_defects.c.id)\
        .join(latest, (latest.c.defect_id == scoped_defects.c.id) & (latest.c.rank == 1))\
        .where(first.c.opened.is_not(None), first.c.opened <= as_of)
    if start is not None:
        cohort_query = cohort_query.where(first.c.opened >= start)
    if end is not None:
        cohort_query = cohort_query.where(first.c.opened < end)
    cohort = cohort_query.cte("defect_cohort")
    c = cohort.c
    valid_resolution = c.resolved >= c.opened
    stats = db.execute(select(func.count().label("total"),
        func.coalesce(func.sum(c.reopened), 0).label("reopened"),
        func.coalesce(func.sum(case((c.status != "Closed", 1), else_=0)), 0).label("open"),
        func.count(case((c.status != "Closed", 1))).label("age_count"),
        func.count(case((valid_resolution, 1))).label("resolution_count"),
        func.avg(case((c.status != "Closed", hours_between(db, as_of, c.opened)))).label("age"),
        func.avg(case((valid_resolution, hours_between(db, c.resolved, c.opened)))).label("resolution"),
    ).select_from(cohort)).one()
    distribution = [dict(row) for row in db.execute(select(c.severity,
        func.count().label("total"),
        func.sum(case((c.status != "Closed", 1), else_=0)).label("open"),
        func.sum(case((c.status == "Closed", 1), else_=0)).label("closed"),
    ).group_by(c.severity).order_by(c.severity)).mappings()]
    # One first-open/first-resolution/first-close event per defect prevents fan-out.
    day_events = union_all(
        select(event_day(db, c.opened).label("date"), c.id, cast(1, Float).label("opened"),
               cast(0, Float).label("resolved"), cast(0, Float).label("closed"),
               cast(1, Float).label("open_delta")),
        select(event_day(db, c.resolved), c.id, cast(0, Float), cast(1, Float), cast(0, Float), cast(0, Float))
            .where(valid_resolution),
        select(event_day(db, c.closed), c.id, cast(0, Float), cast(0, Float), cast(1, Float), cast(0, Float))
            .where(c.closed >= c.opened),
        select(event_day(db, e.at), e.defect_id, cast(0, Float), cast(0, Float), cast(0, Float),
               case((e.to_status == "Closed", -1), else_=1))
            .where(e.defect_id.in_(select(c.id)),
                   or_(e.to_status == "Closed", (e.from_status == "Closed") & (e.to_status == "Open"))),
    ).cte("day_events")
    daily = select(day_events.c.date,
        func.sum(day_events.c.opened).label("opened"),
        func.sum(day_events.c.resolved).label("resolved"),
        func.sum(day_events.c.closed).label("closed"),
        func.sum(day_events.c.open_delta).label("open_delta")).group_by(day_events.c.date).cte("daily")
    burnup = []
    for row in db.execute(select(daily.c.date,
        func.sum(daily.c.opened).over(order_by=daily.c.date).label("opened"),
        func.sum(daily.c.resolved).over(order_by=daily.c.date).label("resolved"),
        func.sum(daily.c.closed).over(order_by=daily.c.date).label("closed"),
        func.sum(daily.c.open_delta).over(order_by=daily.c.date).label("open_remaining"),
    ).order_by(daily.c.date)).mappings():
        point = {key: str(value) if key == "date" else int(value) for key, value in row.items()}
        burnup.append(point)
    return {
        "total_tests": total, "execution_rate": percent(total - totals.not_run, total),
        "pass_rate": percent(totals.passed, totals.passed + totals.failed),
        "open_defects": stats.open, "requirement_coverage": percent(covered_req, req_total),
        "reopen_rate": percent(stats.reopened, stats.total),
        "avg_defect_age_hours": round(float(stats.age), 2) if stats.age is not None else None,
        "avg_resolution_hours": round(float(stats.resolution), 2) if stats.resolution is not None else None,
        "run_series": series, "defect_burnup": burnup, "severity_distribution": distribution,
        "scope": {"project_id": project_id, "release_id": release_id,
                  "start_at": start, "end_at": end, "as_of": as_of,
                  "execution_source": "current interactive execution snapshots", "sprint_available": False,
                  "requirement_scope": "project catalogue links", "run_count": run_count,
                  "run_series_truncated": run_count > 1000},
        "denominators": {"decisive_executions": totals.passed + totals.failed,
            "planned_executions": total, "requirements": req_total, "covered_requirements": covered_req,
            "defects_created": stats.total, "reopened_defects": stats.reopened,
            "open_defects_with_age": stats.age_count, "resolved_defects": stats.resolution_count,
            "defects_missing_creation_history": missing_creation},
    }
