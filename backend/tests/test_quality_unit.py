"""PLN-35: database-free workflow/metrics policy and serialization tests.

Session doubles supply query results. Real SQL populations and persistence are
covered separately by the integration suite; those tests are not counted here.
"""
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql, sqlite

from app import main, metrics, runs
from app.models import Defect, DefectHistory, DefectTransition, Project, Release, User
from app.models import TestCase as Case
from app.models import TestExecution as Execution
from app.models import TestRun as Run
from app.models import TestSuite as Suite

pytestmark = pytest.mark.unit
ADMIN = User(username="admin", role="Admin")


def rule(previous="Open", target="In Progress"):
    return DefectTransition(from_status=previous, to_status=target, allowed_roles=["Admin"])


@pytest.mark.parametrize("statuses,expected", [([], (0, 0, 0)), (["Not Run", "Blocked", "Skipped"], (3, 0, 0)), (["Passed", "Passed", "Failed", "Not Run"], (4, 75, 66.7))])
def test_legacy_metric_denominators(statuses, expected):
    db = MagicMock()
    db.scalars.return_value, db.scalar.return_value = statuses, 2
    value = main.metrics(db)
    assert (value["total_tests"], value["execution_rate"], value["pass_rate"]) == expected
    assert value["open_defects"] == 2


def test_initial_history_and_public_listing():
    db = MagicMock()
    db.scalars.return_value = [rule()]
    value = main.create_defect(main.DefectCreate(title="Incident"), db, ADMIN)
    assert (value["status"], value["allowed"]) == ("Open", ["In Progress"])
    h = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], DefectHistory)]
    assert len(h) == 1 and (h[0].from_status, h[0].to_status) == (None, "Open")
    db.scalars.side_effect = [[rule()], [Defect(id=1, title="A", status="Open")]]
    assert main.list_defects(db, ADMIN)[0]["allowed"] == ["In Progress"]
    db.scalars.side_effect = None
    db.scalars.return_value = h
    assert main.defect_history(1, db)[0]["from"] is None
    assert main.health() == {"status": "ok"}


@pytest.mark.parametrize("body", [main.DefectCreate(title=" "), main.DefectCreate(title="A", test_case="missing")])
def test_bad_creation_does_not_commit(body):
    db = MagicMock()
    db.get.return_value = None
    with pytest.raises(HTTPException) as error:
        main.create_defect(body, db, ADMIN)
    assert error.value.status_code == 422
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("missing,invalid,role,status", [(True, False, "Admin", 404), (False, True, "Admin", 409), (False, False, "Tester", 403)])
def test_transition_errors_preserve_state(missing, invalid, role, status):
    db = MagicMock()
    defect = Defect(id=42, status="Open")
    db.get.side_effect = [None if missing else defect, None if invalid else rule()]
    with pytest.raises(HTTPException) as error:
        main.transition_defect(42, main.Transition(to="In Progress"), db, User(role=role))
    assert error.value.status_code == status
    assert defect.status == "Open"
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("previous,target", [("Open", "In Progress"), ("In Progress", "Resolved"), ("Resolved", "Closed"), ("Resolved", "Open"), ("Closed", "Open")])
def test_transition_adds_exactly_one_history(previous, target):
    db = MagicMock()
    db.get.side_effect = [Defect(id=42, title="Incident", status=previous), rule(previous, target)]
    db.scalars.side_effect = [[], []] if target == "Closed" else [[]]
    assert main.transition_defect(42, main.Transition(to=target), db, ADMIN)["status"] == target
    records = [c.args[0] for c in db.add.call_args_list]
    assert len(records) == 1
    assert (records[0].defect_id, records[0].from_status, records[0].to_status) == (42, previous, target)


@pytest.mark.parametrize("execution,case_status,expected", [("Passed", "Failed", None), ("Failed", "Passed", 409), ("Blocked", "Passed", 409), ("Skipped", "Passed", 409), ("Not Run", "Passed", 409), (None, "Passed", None), (None, "Failed", 409), (None, None, 409)])
def test_verification_uses_latest_execution(execution, case_status, expected):
    db = MagicMock()
    db.scalars.return_value = ["U"]
    db.get.return_value = Case(status=case_status) if case_status else None
    db.scalar.return_value = Execution(status=execution) if execution else None
    if expected:
        with pytest.raises(HTTPException) as error:
            main.require_verification_passed(db, Defect(id=42, test_case="U"))
        assert error.value.status_code == expected
    else:
        main.require_verification_passed(db, Defect(id=42, test_case="U"))


def test_legacy_exception_is_limited_to_documented_seed():
    db = MagicMock()
    db.scalars.return_value, db.scalar.return_value = [], None
    db.get.return_value = Case(status="Not Run")
    main.require_verification_passed(db, Defect(id=3, test_case="TC-005"))


@pytest.mark.parametrize("num,den,expected", [(0, 0, 0), (1, 3, 33.3), (3, 3, 100)])
def test_percentage(num, den, expected):
    assert metrics.percent(num, den) == expected


def test_timezone_validation():
    assert metrics.utc(None) is None
    value = datetime(2026, 1, 1, tzinfo=UTC)
    assert metrics.utc(value) == value
    assert metrics.utc(datetime(2026, 1, 1, 3, tzinfo=timezone(timedelta(hours=3)))) == value
    with pytest.raises(HTTPException) as error:
        metrics.utc(value.replace(tzinfo=None))
    assert error.value.status_code == 422


@pytest.mark.parametrize("dialect", [postgresql.dialect(), sqlite.dialect()])
def test_sql_dialect_expressions_compile(dialect):
    db = MagicMock()
    db.get_bind.return_value.dialect = dialect
    at = datetime(2026, 1, 2, tzinfo=UTC)
    assert str(metrics.hours_between(db, at, datetime(2026, 1, 1, tzinfo=UTC)).compile(dialect=dialect))
    assert str(metrics.event_day(db, at).compile(dialect=dialect))


@pytest.mark.parametrize("kwargs", [{"project_id": 1, "sprint_id": 5}, {"start_at": datetime(2026, 1, 2, tzinfo=UTC), "end_at": datetime(2026, 1, 1, tzinfo=UTC)}, {"project_id": 1, "release_id": 2}])
def test_invalid_metric_scope(kwargs):
    db = MagicMock()
    db.get.return_value = Release(id=2, project_id=3)
    with pytest.raises(HTTPException) as error:
        metrics.expanded_metrics(db, **kwargs)
    assert error.value.status_code == 422


@pytest.mark.parametrize("scope,empty,aware", [(False, True, True), (True, False, False), (True, False, True), ("project", False, True)])
def test_expanded_rates_denominators_and_utc(scope, empty, aware):
    db = MagicMock()
    db.get_bind.return_value.dialect = sqlite.dialect()
    db.get.return_value = Release(id=2, project_id=1)
    at = datetime(2026, 1, 1, tzinfo=UTC if aware else None)
    class Totals(tuple):
        passed = property(lambda s: s[0])
        failed = property(lambda s: s[1])
        not_run = property(lambda s: s[4])
    totals = Totals((0, 0, 0, 0, 0) if empty else (6, 2, 1, 1, 2))
    stat = NS(total=0 if empty else 4, reopened=0 if empty else 1, open=0 if empty else 2,
              age_count=0 if empty else 2, resolution_count=0 if empty else 3,
              age=None if empty else 12.345, resolution=None if empty else 4.567)
    point = dict(run_id=1, run_name="Run", executed_at=at, passed=6, failed=2, blocked=1, skipped=1, not_run=2)
    responses = [MagicMock() for _ in range(5)]
    responses[0].one.return_value = totals
    responses[1].mappings.return_value = [] if empty else [point]
    responses[2].one.return_value = stat
    responses[3].mappings.return_value = [] if empty else [{"severity": "High", "total": 4, "open": 2, "closed": 2}]
    responses[4].mappings.return_value = [] if empty else [{"date": "2026-01-01", "opened": 4, "resolved": 3, "closed": 2, "open_remaining": 2}]
    db.execute.side_effect = responses
    db.scalar.side_effect = [0 if empty else 1001, 0 if empty else 4, 0 if empty else 3, 0]
    kwargs = dict(project_id=1, release_id=2, start_at=datetime(2025, 1, 1, tzinfo=UTC), end_at=datetime(2027, 1, 1, tzinfo=UTC)) if scope else {}
    if scope == "project":
        kwargs = {"project_id": 1}
    value = metrics.expanded_metrics(db, **kwargs)
    assert value["total_tests"] == sum(totals)
    assert value["pass_rate"] == (0 if empty else 75)
    assert value["requirement_coverage"] == (0 if empty else 75)
    assert value["reopen_rate"] == (0 if empty else 25)
    assert value["avg_defect_age_hours"] == (None if empty else 12.35)
    assert value["scope"]["run_series_truncated"] is (not empty)
    if not empty:
        assert value["run_series"][0]["executed_at"].tzinfo == UTC
        assert value["defect_burnup"][0]["open_remaining"] == 2
        assert value["denominators"]["planned_executions"] == 12


@pytest.mark.parametrize("missing", [True, False])
def test_run_lookup(missing):
    db = MagicMock()
    run = Run(id=7, name="Run", project_id=1, created_by="tester", executions=[])
    db.scalar.return_value = None if missing else run
    if missing:
        with pytest.raises(HTTPException) as error:
            runs.get_test_run(7, db)
        assert error.value.status_code == 404
    else:
        assert runs.get_test_run(7, db)["name"] == "Run"
        db.scalars.return_value = [run]
        assert runs.list_test_runs(db)[0]["id"] == 7


@pytest.mark.parametrize("which", ["project", "release", "suite", "case"])
def test_invalid_run_relations(which):
    db = MagicMock()
    db.get.side_effect = lambda model, key: (None if which == "project" else Project(id=1)) if model is Project else (Release(project_id=2) if model is Release else Suite(project_id=2))
    db.scalars.return_value = []
    body = runs.TestRunCreate(name="Run", project_id=1, test_case_ids=["U"], release_id=2 if which == "release" else None, suite_id=2 if which == "suite" else None)
    with pytest.raises(HTTPException) as error:
        runs.create_test_run(body, db, ADMIN)
    assert error.value.status_code == 422
    db.commit.assert_not_called()


def test_run_case_deduplication():
    db = MagicMock()
    db.get.return_value = NS(project_id=1)
    db.scalars.return_value = ["U"]
    db.scalar.return_value = Run(id=1, name="Run", project_id=1, executions=[])
    body = runs.TestRunCreate(name="Run", project_id=1, release_id=2, suite_id=3, test_case_ids=["U", "U"])
    assert runs.create_test_run(body, db, ADMIN)["name"] == "Run"
    executions = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], Execution)]
    assert len(executions) == 1 and executions[0].status == "Not Run"


@pytest.mark.parametrize("found,case_exists,links", [(False, False, None), (True, True, None), (True, False, [9]), (True, True, [])])
def test_record_result(found, case_exists, links):
    db = MagicMock()
    ex = Execution(id=3, run_id=1, test_case_id="U", defects=[])
    db.scalar.return_value = ex if found else None
    case = Case(id="U", status="Not Run")
    db.get.return_value = case if case_exists else None
    db.scalars.return_value = [Defect(id=9)] if links else []
    body = runs.ExecutionRecord(status="Passed", actual_result="verified", notes="unit", defect_ids=links)
    if not found:
        with pytest.raises(HTTPException) as error:
            runs.record_execution(1, 3, body, db, ADMIN)
        assert error.value.status_code == 404
        return
    value = runs.record_execution(1, 3, body, db, ADMIN)
    assert (value["status"], value["actual_result"], value["defect_ids"]) == ("Passed", "verified", links or [])
    if case_exists:
        assert case.status == "Passed"


def test_missing_defect_does_not_change_execution():
    db = MagicMock()
    ex = Execution(id=3, status="Failed", test_case_id="U", defects=[])
    db.scalar.return_value, db.scalars.return_value = ex, []
    with pytest.raises(HTTPException) as error:
        runs.record_execution(1, 3, runs.ExecutionRecord(status="Passed", defect_ids=[9]), db, ADMIN)
    assert error.value.status_code == 422 and ex.status == "Failed"
    db.commit.assert_not_called()


def test_execution_incident_history_and_case_link():
    db = MagicMock()
    ex = Execution(id=3, test_case_id="U", defects=[])
    db.scalar.return_value, db.scalars.return_value = ex, [rule()]
    value = runs.create_defect_from_execution(1, 3, runs.ExecutionDefectCreate(title="Incident"), db, ADMIN)
    assert (value["test_case"], value["status"], value["allowed"]) == ("U", "Open", ["In Progress"])
    assert ex.defects[0].title == "Incident"
    histories = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], DefectHistory)]
    assert len(histories) == 1 and histories[0].from_status is None
