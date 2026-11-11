"""Unit checks for the R3/R4 defect response contract; no database access."""
import pytest

from app.main import DefectCreate, defect_out
from app.models import Defect

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(("status", "allowed"), [
    ("Open", ["In Progress"]),
    ("In Progress", ["Resolved"]),
    ("Resolved", ["Closed", "Open"]),
    ("Closed", ["Open"]),
])
def test_defect_response_exposes_only_legal_actions(status, allowed):
    defect = Defect(id=42, title="Response contract", severity="High",
                    status=status, test_case="TC-003")
    assert defect_out(defect) == {
        "id": 42, "title": "Response contract", "severity": "High",
        "status": status, "test_case": "TC-003", "allowed": allowed,
    }


def test_defect_creation_defaults_support_an_unlinked_case():
    body = DefectCreate(title="Standalone defect")
    assert body.severity == "Medium"
    assert body.test_case is None
