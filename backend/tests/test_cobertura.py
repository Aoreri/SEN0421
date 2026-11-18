"""PLN-23/R5/R6: evidence counters, safe XML and atomic coverage persistence."""
import pytest
from sqlalchemy import func, select

from app.cobertura import MAX_COVERAGE_BYTES, parse_cobertura
from app.db import SessionLocal
from app.models import CoverageImport
from tests.conftest import as_user

REPORT = '''<?xml version="1.0"?>
<!DOCTYPE coverage SYSTEM "http://cobertura.sourceforge.net/xml/coverage-04.dtd">
<coverage lines-valid="2" lines-covered="1" branches-valid="2" branches-covered="1"
 line-rate="0.5" branch-rate="0.5"><sources><source>/ignored/source</source></sources>
<packages><package name="app"><classes><class filename="app/main.py" name="main">
<methods><method name="example"><lines><line number="1" hits="1"/></lines></method></methods>
<lines><line number="1" hits="2" branch="true" condition-coverage="50% (1/2)"/>
<line number="2" hits="0"/></lines></class></classes></package></packages></coverage>'''


@pytest.mark.unit
def test_counters_are_computed_from_lines_and_method_lines_are_not_double_counted():
    result = parse_cobertura(REPORT.encode())
    assert result['summary'] == {'lines_valid': 2, 'lines_covered': 1,
        'branches_valid': 2, 'branches_covered': 1, 'line_coverage': 50.0, 'branch_coverage': 50.0}
    assert result['files'][0]['filename'] == 'app/main.py'


@pytest.mark.unit
@pytest.mark.parametrize('xml', [
    '', '<bad/>', '<coverage>',
    REPORT.replace('lines-covered="1"', 'lines-covered="2"'),
    REPORT.replace('line-rate="0.5"', 'line-rate="NaN"'),
    REPORT.replace('filename="app/main.py"', 'filename="../private"'),
    REPORT.replace('filename="app/main.py"', 'filename="/etc/passwd"'),
    REPORT.replace('hits="0"', 'hits="-1"'),
    REPORT.replace('number="2"', 'number="1"'),
    REPORT.replace('condition-coverage="50% (1/2)"', 'condition-coverage="50% (3/2)"'),
    REPORT.replace('condition-coverage="50% (1/2)"', ''),
    REPORT.replace('<line number="2" hits="0"/>', '<wrapper><line number="2" hits="0"/></wrapper>'),
    '<!DOCTYPE coverage [<!ENTITY secret SYSTEM "file:///etc/passwd">]><coverage>&secret;</coverage>',
], ids=["empty", "wrong-root", "malformed", "counter-mismatch", "nan-rate",
        "parent-path", "absolute-path", "negative-hits", "duplicate-line",
        "branch-overflow", "missing-branch-evidence", "hidden-lines", "external-entity"])
def test_invalid_or_inconsistent_reports_are_rejected(xml):
    with pytest.raises(ValueError):
        parse_cobertura(xml.encode())


@pytest.mark.unit
def test_limits_and_zero_denominator():
    with pytest.raises(ValueError):
        parse_cobertura(b' ' * (MAX_COVERAGE_BYTES + 1))
    empty = b'<coverage lines-valid="0" lines-covered="0" branches-valid="0" branches-covered="0"/>'
    assert parse_cobertura(empty)['summary']['line_coverage'] == 0.0


def upload(client, xml=REPORT, project=1, username='tester', params=None):
    headers = {'Content-Type': 'application/xml'}
    if username:
        headers.update(as_user(username))
    return client.post(f'/api/projects/{project}/coverage/import', content=xml,
                       headers=headers, params=params or {})


@pytest.mark.integration
@pytest.mark.usefixtures('fresh_seed')
def test_import_persists_metadata_and_linked_junit_evidence(client, record_property):
    record_property("test_case_id", "TC-005")
    junit = client.post('/api/projects/1/runs/import',
                        content='<testsuite><testcase name="TC-005"/></testsuite>',
                        headers={**as_user('tester'), 'Content-Type': 'application/xml'},
                        params={'commit': 'a' * 40, 'branch': 'feature/ci'}).json()
    response = upload(client, params={'junit_import_id': junit['id']})
    assert response.status_code == 201, response.text
    report = response.json()
    assert report['commit'] == 'a' * 40 and report['branch'] == 'feature/ci'
    assert report['summary']['line_coverage'] == 50.0
    auth = as_user('developer')
    assert client.get(f"/api/projects/1/coverage/imports/{report['id']}", headers=auth).json() == report
    listing = client.get('/api/projects/1/coverage/imports', headers=auth).json()
    assert listing[0]['id'] == report['id'] and 'files' not in listing[0]
    assert client.delete('/api/projects/1', headers=as_user('admin')).status_code == 409
    assert upload(client, params={'junit_import_id': junit['id'], 'branch': 'other'}).status_code == 422
    assert upload(client, project=99999).status_code == 404
    assert client.get(f"/api/projects/999/coverage/imports/{report['id']}", headers=auth).status_code == 404
    other = client.post('/api/projects', json={'name': 'Other'}, headers=as_user('admin')).json()
    assert upload(client, project=other['id'], params={'junit_import_id': junit['id']}).status_code == 422


@pytest.mark.integration
@pytest.mark.usefixtures('fresh_seed')
@pytest.mark.parametrize(('username', 'expected'), [(None, 401), ('developer', 403),
    ('tester', 201), ('testlead', 201), ('admin', 201)])
def test_import_roles(client, username, expected):
    assert upload(client, username=username).status_code == expected


@pytest.mark.integration
@pytest.mark.usefixtures('fresh_seed')
def test_invalid_report_never_writes_and_read_auth_is_required(client):
    assert upload(client, xml=REPORT.replace('lines-valid="2"', 'lines-valid="3"')).status_code == 422
    assert upload(client, params={'branch': 'bad\x00branch'}).status_code == 422
    assert upload(client, xml=' ' * (MAX_COVERAGE_BYTES + 1)).status_code == 413
    assert client.post('/api/projects/1/coverage/import', json={}, headers=as_user('tester')).status_code == 415
    assert client.get('/api/projects/1/coverage/imports').status_code == 401
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(CoverageImport)) == 0
