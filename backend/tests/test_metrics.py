"""PLN-24/R5: exact SQL populations, duplicate links and time boundaries."""
from datetime import UTC, datetime

import pytest

from app.db import SessionLocal
from app.models import (
    Defect,
    DefectHistory,
    Project,
    Release,
    Requirement,
    execution_defects,
)
from app.models import (
    TestCase as CaseModel,
)
from app.models import (
    TestExecution as ExecutionModel,
)
from app.models import (
    TestRun as RunModel,
)
from tests.conftest import as_user

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('fresh_seed')]


@pytest.fixture(autouse=True)
def auth_client(fresh_seed, client):
    client.headers.update(as_user('tester'))


def at(day):
    return datetime(2026, 11, day, tzinfo=UTC)


@pytest.fixture
def population():
    with SessionLocal() as db:
        p = Project(name='PLN-24 fixture')
        db.add(p)
        db.flush()
        a, b = [Release(project_id=p.id, version=v) for v in ('A', 'B')]
        reqs = [Requirement(id=f'R24-{i}', project_id=p.id, title=f'Req {i}') for i in range(3)]
        cases = [CaseModel(id=f'T24-{i}', title=f'Case {i}', requirement=reqs[0].id,
                          requirements=reqs[:2] if i == 0 else reqs[:1]) for i in range(6)]
        db.add_all([a, b, *reqs, *cases])
        db.flush()
        ra = RunModel(name='A run', project_id=p.id, release_id=a.id, created_by='tester', created_at=at(1))
        rb = RunModel(name='B run', project_id=p.id, release_id=b.id, created_by='tester', created_at=at(10))
        db.add_all([ra, rb])
        db.flush()
        ex = [ExecutionModel(run_id=ra.id, test_case_id=tc.id, status=status) for tc, status in
              zip(cases, ['Passed', 'Passed', 'Failed', 'Blocked', 'Skipped', 'Not Run'])]
        db.add_all([*ex, ExecutionModel(run_id=rb.id, test_case_id=cases[0].id, status='Failed')])
        ds = [Defect(title=f'Defect {i}', test_case=cases[0].id, severity='High',
                     status='Closed' if i == 1 else 'Open') for i in range(3)]
        db.add_all(ds)
        db.flush()
        histories = [
            [(None, 'Open', 1), ('Open', 'In Progress', 1), ('In Progress', 'Resolved', 2),
             ('Resolved', 'Open', 3), ('Open', 'In Progress', 3), ('In Progress', 'Resolved', 4),
             ('Resolved', 'Closed', 5), ('Closed', 'Open', 6)],
            [(None, 'Open', 2), ('Open', 'In Progress', 2), ('In Progress', 'Resolved', 3),
             ('Resolved', 'Closed', 4)], [(None, 'Open', 3)],
        ]
        for d, history in zip(ds, histories):
            for previous, new, day in history:
                db.add(DefectHistory(defect_id=d.id, from_status=previous, to_status=new, at=at(day)))
        db.execute(execution_defects.insert(), [
            {'execution_id': ex[0].id, 'defect_id': ds[0].id},
            {'execution_id': ex[1].id, 'defect_id': ds[0].id},
            {'execution_id': ex[2].id, 'defect_id': ds[1].id}])
        db.commit()
        return {'project_id': p.id, 'release_id': a.id, 'other_release': b.id}


def get(client, population, **params):
    r = client.get('/api/metrics/expanded', params={'release_id': population['release_id'], **params})
    assert r.status_code == 200, r.text
    return r.json()


def test_release_aggregates_no_fanout_and_first_resolution(client, population):
    r = get(client, population)
    assert (r['total_tests'], r['execution_rate'], r['pass_rate']) == (6, 83.3, 66.7)
    assert r['requirement_coverage'] == 66.7
    assert r['reopen_rate'] == 50.0 and r['open_defects'] == 1
    assert r['avg_resolution_hours'] == 24.0
    expected = (datetime.fromisoformat(r['scope']['as_of']) - at(1)).total_seconds() / 3600
    assert r['avg_defect_age_hours'] == pytest.approx(expected, abs=0.01)
    assert r['denominators']['defects_created'] == 2
    assert r['denominators']['reopened_defects'] == 1
    assert r['run_series'][0]['blocked'] == 1 and r['run_series'][0]['not_run'] == 1
    assert r['severity_distribution'] == [{'severity': 'High', 'total': 2, 'open': 1, 'closed': 1}]
    assert r['defect_burnup'][-1] == {'date': '2026-11-06', 'opened': 2, 'resolved': 2,
                                     'closed': 2, 'open_remaining': 1}


def test_period_cohort_and_exclusive_end(client, population):
    r = get(client, population, start_at=at(1).isoformat(), end_at=at(3).isoformat())
    assert r['reopen_rate'] == 0.0
    assert r['denominators']['defects_created'] == 2 and r['open_defects'] == 2
    assert r['avg_resolution_hours'] == 24.0
    r = get(client, population, start_at=at(2).isoformat(), end_at=at(5).isoformat())
    assert r['total_tests'] == 0 and r['denominators']['defects_created'] == 1
    assert r['open_defects'] == 0 and r['reopen_rate'] == 0


def test_project_and_release_membership_are_distinct(client, population):
    r = client.get('/api/metrics/expanded', params={'project_id': population['project_id']}).json()
    assert r['total_tests'] == 7 and r['pass_rate'] == 50
    assert r['denominators']['defects_created'] == 3 and r['open_defects'] == 2
    assert r['reopen_rate'] == 33.3
    assert get(client, population, release_id=population['other_release'])['open_defects'] == 0


def test_empty_and_legacy_contract(client):
    with SessionLocal() as db:
        p = Project(name='Empty metrics')
        db.add(p)
        db.commit()
        project_id = p.id
    r = client.get('/api/metrics/expanded', params={'project_id': project_id}).json()
    assert r['total_tests'] == r['pass_rate'] == r['requirement_coverage'] == r['reopen_rate'] == 0
    assert r['avg_defect_age_hours'] is None and r['avg_resolution_hours'] is None
    assert r['run_series'] == [] and r['defect_burnup'] == []
    assert client.get('/api/metrics').json() == {
        'total_tests': 6, 'execution_rate': 66.7, 'pass_rate': 75, 'open_defects': 3}


@pytest.mark.parametrize('params', [{'sprint_id': 'sprint-1'}, {'start_at': '2026-11-01T00:00:00'},
    {'start_at': at(3).isoformat(), 'end_at': at(2).isoformat()}, {'release_id': -1}, {'project_id': -1}])
def test_invalid_or_missing_model_scope(client, params):
    assert client.get('/api/metrics/expanded', params=params).status_code == 422


def test_unknown_or_cross_project_scope(client, population):
    for params in ({'release_id': 99999}, {'project_id': 99999}):
        assert client.get('/api/metrics/expanded', params=params).status_code == 404
    assert client.get('/api/metrics/expanded', params={
        'release_id': population['release_id'], 'project_id': 1}).status_code == 422


def test_all_not_run_and_missing_creation_history_are_explicit(client, population):
    with SessionLocal() as db:
        from sqlalchemy import update
        db.execute(update(ExecutionModel).values(status='Not Run'))
        db.add(Defect(title='No history', test_case='T24-0', severity='Low', status='Open'))
        db.commit()
    result = client.get('/api/metrics/expanded', params={'project_id': population['project_id']}).json()
    assert result['total_tests'] == 7 and result['execution_rate'] == result['pass_rate'] == 0
    assert result['denominators']['defects_missing_creation_history'] == 1
    assert result['denominators']['defects_created'] == 3


def test_run_timestamp_has_utc_offset_and_can_be_reused_as_filter(client, population):
    report = get(client, population)
    timestamp = report['run_series'][0]['executed_at']
    assert datetime.fromisoformat(timestamp) == at(1)
    assert timestamp.endswith('+00:00') or timestamp.endswith('Z')
    assert client.get('/api/metrics/expanded', params={
        'release_id': population['release_id'], 'start_at': timestamp,
    }).status_code == 200


@pytest.mark.parametrize('reopen_from', ['Resolved', 'Closed'])
def test_reopen_day_is_visible_without_double_counting_active_defects(client, population, reopen_from):
    with SessionLocal() as db:
        from sqlalchemy import select
        execution = db.scalar(select(ExecutionModel).join(RunModel).where(
            RunModel.release_id == population['other_release']))
        defect = Defect(title='Reopen regression', test_case='T24-0', severity='High', status='Open')
        db.add(defect)
        db.flush()
        history = [(None, 'Open', 1), ('Open', 'In Progress', 1), ('In Progress', 'Resolved', 2)]
        if reopen_from == 'Closed':
            history.append(('Resolved', 'Closed', 2))
        history.append((reopen_from, 'Open', 3))
        for previous, new, day in history:
            db.add(DefectHistory(defect_id=defect.id, from_status=previous, to_status=new, at=at(day)))
        db.execute(execution_defects.insert().values(execution_id=execution.id, defect_id=defect.id))
        db.commit()
    report = get(client, population, release_id=population['other_release'])
    points = {point['date']: point for point in report['defect_burnup']}
    assert '2026-11-03' in points
    assert points['2026-11-02']['open_remaining'] == (0 if reopen_from == 'Closed' else 1)
    assert points['2026-11-03']['open_remaining'] == report['open_defects'] == 1
    assert points['2026-11-03']['opened'] == points['2026-11-03']['resolved'] == 1
    assert report['reopen_rate'] == 100.0
