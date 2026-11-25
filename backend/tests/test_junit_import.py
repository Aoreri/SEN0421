"""PLN-22/R6: authenticated, atomic persistence and project-scoped JUnit mapping."""
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.junit import MAX_XML_BYTES
from app.models import ImportedTestResult, ImportedTestRun
from tests.conftest import as_user

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("fresh_seed")]

REPORT = '''<testsuites><testsuite name="CI">
  <testcase name="test_login" classname="auth" time="0.25"><properties>
    <property name="test_case_id" value="TC-001"/>
  </properties></testcase>
  <testcase name="TC-003"><failure message="failed assertion">diagnostic</failure></testcase>
  <testcase name="TC-005"><skipped/></testcase>
  <testcase name="TC-MISSING"><error message="setup failed"/></testcase>
</testsuite></testsuites>'''


def upload(client, xml=REPORT, project=1, username="tester", params=None):
    headers = {"Content-Type": "application/xml"}
    if username:
        headers.update(as_user(username))
    return client.post(f"/api/projects/{project}/runs/import", content=xml,
                       headers=headers, params=params or {})


def counts():
    with SessionLocal() as db:
        return (db.scalar(select(func.count()).select_from(ImportedTestRun)),
                db.scalar(select(func.count()).select_from(ImportedTestResult)))


def test_import_persists_metadata_mapping_outcomes_and_unmatched_report(client):
    old_cases = client.get('/api/test-cases', headers=as_user('tester')).json()
    old_metrics = client.get('/api/metrics', headers=as_user('tester')).json()
    response = upload(client, params={"commit": "a" * 40, "branch": "feature/import"})
    assert response.status_code == 201, response.text
    report = response.json()
    assert report['commit'] == 'a' * 40 and report['branch'] == 'feature/import'
    assert report['project_id'] == 1 and report['created_at']
    assert report['summary'] == {
        'total': 4, 'matched': 3, 'unmatched': 1, 'passed': 1, 'failed': 2, 'skipped': 1,
    }
    assert [r['test_case_id'] for r in report['results']] == ['TC-001', 'TC-003', 'TC-005', None]
    assert report['unmatched_results'][0]['reported_key'] == 'TC-MISSING'
    assert report['unmatched_results'][0]['unmatched_reason'] == 'unknown_test_case'
    assert report['results'][1]['message'] == 'failed assertion\ndiagnostic'
    assert counts() == (1, 4)
    # A fresh request/session must read the same persisted summary and results.
    saved = client.get(f"/api/projects/1/runs/imports/{report['id']}",
                       headers=as_user('developer'))
    assert saved.status_code == 200 and saved.json() == report
    listing = client.get('/api/projects/1/runs/imports', headers=as_user('tester')).json()
    assert listing[0]['summary'] == report['summary'] and 'results' not in listing[0]
    assert client.get('/api/test-cases', headers=as_user('tester')).json() == old_cases
    # PLN-33 creates one Open incident for the matched failed TC-003 result.
    old_metrics['open_defects'] += 1
    assert client.get('/api/metrics', headers=as_user('tester')).json() == old_metrics


@pytest.mark.parametrize('username', ['admin', 'testlead', 'tester'])
def test_import_roles_are_allowed(client, username):
    assert upload(client, username=username).status_code == 201


@pytest.mark.parametrize(('username', 'status'), [(None, 401), ('developer', 403)])
def test_import_auth_is_enforced_before_writes(client, username, status):
    assert upload(client, username=username).status_code == status
    assert counts() == (0, 0)


def test_other_project_cases_are_reported_unmatched_and_reads_are_scoped(client):
    project = client.post('/api/projects', json={'name': 'Other'}, headers=as_user('admin')).json()
    report = upload(client, project=project['id']).json()
    assert report['summary']['matched'] == 0 and report['summary']['unmatched'] == 4
    assert report['unmatched_results'][0]['unmatched_reason'] == 'not_linked_to_project'
    assert client.get(f"/api/projects/1/runs/imports/{report['id']}",
                      headers=as_user('admin')).status_code == 404
    assert client.get('/api/projects/1/runs/imports', headers=as_user('admin')).json() == []
    assert upload(client, project=99999).status_code == 404
    assert counts() == (1, 4)


@pytest.mark.parametrize('xml', [
    '<testsuite><testcase name="TC-001"/><wrapper><testcase name="TC-002"/></wrapper></testsuite>',
    '<bad/>', '<testsuite/>', '<testsuite>',
    '<testsuite><testcase name="TC-001"/><testcase name="TC-002" time="NaN"/></testsuite>',
    '<!DOCTYPE testsuite [<!ENTITY x "bad">]><testsuite><testcase name="&x;"/></testsuite>'])
def test_bad_report_rejects_every_result_atomically(client, xml):
    assert upload(client, xml=xml).status_code == 422
    assert counts() == (0, 0)


def test_wrong_media_type_size_and_metadata_limits(client):
    headers = as_user('tester')
    assert client.post('/api/projects/1/runs/import', json={'xml': REPORT},
                       headers=headers).status_code == 415
    assert upload(client, xml=' ' * (MAX_XML_BYTES + 1)).status_code == 413
    for params in ({'commit': 'not-a-sha'}, {'branch': ' '}, {'branch': 'a' * 256},
                   {'branch': 'bad\x00branch'}):
        assert upload(client, params=params).status_code == 422
    assert counts() == (0, 0)


def test_repeated_case_keys_and_repeated_imports_are_not_silently_dropped(client):
    xml = '<testsuite><testcase name="TC-001"/><testcase name="TC-001"/></testsuite>'
    first, second = upload(client, xml=xml).json(), upload(client, xml=xml).json()
    assert first['id'] != second['id']
    assert first['summary']['matched'] == 2
    assert [r['position'] for r in first['results']] == [0, 1]
    assert counts() == (2, 4)


def test_constraint_failure_rolls_back_complete_import(client, monkeypatch):
    original = SessionLocal.class_.flush

    def fail_for_results(session, *args, **kwargs):
        if any(isinstance(row, ImportedTestResult) for row in session.new):
            raise IntegrityError('forced constraint failure', {}, Exception('test'))
        return original(session, *args, **kwargs)

    monkeypatch.setattr(SessionLocal.class_, 'flush', fail_for_results)
    assert upload(client).status_code == 409
    assert counts() == (0, 0)


def test_reads_require_login_and_support_pagination(client):
    assert client.get('/api/projects/1/runs/imports').status_code == 401
    upload(client)
    upload(client)
    headers = as_user('tester')
    assert len(client.get('/api/projects/1/runs/imports?limit=1&offset=1', headers=headers).json()) == 1
    assert client.get('/api/projects/1/runs/imports?limit=0', headers=headers).status_code == 422
    assert client.get('/api/projects/1/runs/imports/99999', headers=headers).status_code == 404


def test_project_with_import_history_cannot_be_deleted(client):
    project = client.post('/api/projects', json={'name': 'Import-only project'},
                          headers=as_user('admin')).json()
    report = upload(client, project=project['id']).json()
    assert client.delete(f"/api/projects/{project['id']}",
                         headers=as_user('admin')).status_code == 409
    assert client.get(f"/api/projects/{project['id']}/runs/imports/{report['id']}",
                      headers=as_user('tester')).status_code == 200
