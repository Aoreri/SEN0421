"""PLN-33/R4/R6: atomic, concurrent and project-scoped failure incidents."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal, engine
from app.main import app
from app.models import Defect, DefectHistory, ImportedTestResult, ImportedTestRun, JUnitAutoDefect
from tests.conftest import as_user
from tests.test_junit_import import upload

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('fresh_seed')]

FAILURE = '''<testsuite name="CI"><testcase name="test_login[param]" classname="auth" time="0.2">
<properties><property name="test_case_id" value="TC-001"/></properties>
<failure type="AssertionError" message="expected 200">actual 500</failure>
</testcase></testsuite>'''


def row_counts():
    with SessionLocal() as db:
        return tuple(db.scalar(select(func.count()).select_from(model)) for model in (
            ImportedTestRun, ImportedTestResult, Defect, DefectHistory, JUnitAutoDefect))


def result(client, xml=FAILURE, **kwargs):
    response = upload(client, xml, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


def test_failed_matched_result_creates_open_defect_and_exactly_one_creation_history(client):
    before = row_counts()
    cases = client.get('/api/test-cases', headers=as_user('tester')).json()
    report = result(client)
    row = report['results'][0]
    assert len(row['failure_signature']) == 64 and row['defect_id'] is not None
    defect = next(d for d in client.get('/api/defects', headers=as_user('tester')).json() if d['id'] == row['defect_id'])
    assert defect['status'] == 'Open' and defect['test_case'] == 'TC-001'
    assert defect['severity'] == 'Medium'
    history = client.get(f"/api/defects/{defect['id']}/history", headers=as_user('tester')).json()
    assert len(history) == 1 and history[0]['from'] is None and history[0]['to'] == 'Open'
    assert row_counts() == tuple(n + 1 for n in before)
    assert client.get('/api/test-cases', headers=as_user('tester')).json() == cases
    saved = client.get(f"/api/projects/1/runs/imports/{report['id']}",
                       headers=as_user('developer')).json()
    assert saved == report


def test_repeat_import_and_duplicate_results_reuse_incident_across_commit_branch_and_name(client):
    first = result(client)['results'][0]
    before = row_counts()
    changed = FAILURE.replace('test_login[param]', 'renamed_login').replace('time="0.2"', 'time="7"')
    changed = changed.replace('expected 200', ' expected\n  200 ').replace('actual 500', 'actual   500')
    second = result(client, changed, params={'commit': 'a' * 40, 'branch': 'other'})
    row = second['results'][0]
    assert row['defect_id'] == first['defect_id']
    assert row['failure_signature'] == first['failure_signature']
    repeated = FAILURE.replace('</testcase></testsuite>', '</testcase>')
    repeated = repeated + '<testcase name="TC-001"><failure type="AssertionError" message="expected 200">actual 500</failure></testcase></testsuite>'
    duplicate_rows = result(client, repeated)['results']
    assert all(r['defect_id'] == first['defect_id'] for r in duplicate_rows)
    after = row_counts()
    assert after[2:] == before[2:]  # No extra defect, history or deduplication key.
    assert after[0] == before[0] + 2 and after[1] == before[1] + 3


@pytest.mark.parametrize('replacement', [
    ('actual 500', 'actual 403'), ('AssertionError', 'TimeoutError'),
    ('<failure ', '<error '), ('TC-001', 'TC-003'),
])
def test_distinct_errors_or_test_cases_create_distinct_incidents(client, replacement):
    first = result(client)['results'][0]
    changed = FAILURE.replace(*replacement)
    if replacement[0] == '<failure ':
        changed = changed.replace('</failure>', '</error>')
    second = result(client, changed)['results'][0]
    assert first['defect_id'] != second['defect_id']


def test_same_key_in_another_project_is_not_deduplicated_across_projects(client):
    first = result(client)['results'][0]
    project = client.post('/api/projects', json={'name': 'Second failure scope'},
                          headers=as_user('admin')).json()
    requirement = client.post('/api/requirements', json={
        'id': 'R33', 'project_id': project['id'], 'title': 'Other project requirement',
    }, headers=as_user('admin'))
    assert requirement.status_code == 201
    response = client.put('/api/requirements/R33/test-cases',
                          json={'test_cases': ['TC-001']}, headers=as_user('tester'))
    assert response.status_code == 200
    second = result(client, project=project['id'])['results'][0]
    assert first['failure_signature'] == second['failure_signature']
    assert first['defect_id'] != second['defect_id']


@pytest.mark.parametrize('xml', [
    '<testsuite><testcase name="TC-001"/></testsuite>',
    '<testsuite><testcase name="TC-001"><skipped/></testcase></testsuite>',
    '<testsuite><testcase name="UNKNOWN"><failure/></testcase></testsuite>',
])
def test_passed_skipped_and_unmatched_failures_do_not_create_defects(client, xml):
    before = row_counts()
    row = result(client, xml)['results'][0]
    assert row['defect_id'] is None and row_counts()[2:] == before[2:]


def test_known_case_outside_project_creates_no_defect(client):
    project = client.post('/api/projects', json={'name': 'No linked tests'},
                          headers=as_user('admin')).json()
    before = row_counts()
    report = result(client, project=project['id'])
    assert report['results'][0]['defect_id'] is None
    assert report['unmatched_results'][0]['unmatched_reason'] == 'not_linked_to_project'
    assert row_counts()[2:] == before[2:]


@pytest.mark.parametrize('final_status', ['Resolved', 'Closed'])
def test_later_pass_or_repeat_does_not_change_existing_defect_lifecycle(client, final_status):
    first = result(client)['results'][0]
    # Existing workflow remains the only authority for status changes.
    targets = ['In Progress', 'Resolved'] + (['Closed'] if final_status == 'Closed' else [])
    for target in targets:
        response = client.post(f"/api/defects/{first['defect_id']}/transition",
                               json={'to': target}, headers=as_user('admin'))
        assert response.status_code == 200
    before = row_counts()
    assert result(client)['results'][0]['defect_id'] == first['defect_id']
    result(client, '<testsuite><testcase name="TC-001"/></testsuite>')
    with SessionLocal() as db:
        assert db.get(Defect, first['defect_id']).status == final_status
    assert row_counts()[2:] == before[2:]


@pytest.mark.parametrize('fail_on', [DefectHistory, ImportedTestResult])
def test_failure_rolls_back_import_defect_key_and_creation_history(client, monkeypatch, fail_on):
    before = row_counts()
    original = SessionLocal.class_.flush

    def fail(session, *args, **kwargs):
        if any(isinstance(row, fail_on) for row in session.new):
            raise IntegrityError('PLN-33 injected write failure', {}, Exception('test'))
        return original(session, *args, **kwargs)

    monkeypatch.setattr(SessionLocal.class_, 'flush', fail)
    assert upload(client, FAILURE).status_code == 409
    assert row_counts() == before


@pytest.mark.postgres
def test_concurrent_imports_share_one_incident_and_leave_no_orphan(client, monkeypatch):
    if engine.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL unique-key race regression')
    headers = {**as_user('tester'), 'Content-Type': 'application/xml'}
    before = row_counts()
    barrier = Barrier(2)
    original = SessionLocal.class_.flush

    def synchronize_candidates(session, *args, **kwargs):
        if any(isinstance(row, JUnitAutoDefect) for row in session.new):
            barrier.wait(timeout=15)
        return original(session, *args, **kwargs)

    monkeypatch.setattr(SessionLocal.class_, 'flush', synchronize_candidates)

    def submit():
        with TestClient(app) as parallel:
            return parallel.post('/api/projects/1/runs/import', content=FAILURE, headers=headers)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit) for _ in range(2)]
        responses = [future.result(timeout=30) for future in futures]
    assert [response.status_code for response in responses] == [201, 201]
    ids = {response.json()['results'][0]['defect_id'] for response in responses}
    assert len(ids) == 1
    after = row_counts()
    assert after == (before[0] + 2, before[1] + 2, before[2] + 1, before[3] + 1, before[4] + 1)
