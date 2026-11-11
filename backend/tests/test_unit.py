"""Unit checks for the R3/R4 defect response contract; no database access."""
import pytest

from app.main import DefectCreate, defect_out
from app.models import Defect, DefectTransition, User

pytestmark = pytest.mark.unit

RULES = [
    DefectTransition(from_status="Open", to_status="In Progress",
                     allowed_roles=["Developer", "Admin"]),
    DefectTransition(from_status="In Progress", to_status="Resolved",
                     allowed_roles=["Developer", "Admin"]),
    DefectTransition(from_status="Resolved", to_status="Closed",
                     allowed_roles=["Tester", "Test Lead", "Admin"]),
    DefectTransition(from_status="Resolved", to_status="Open",
                     allowed_roles=["Tester", "Test Lead", "Admin"]),
    DefectTransition(from_status="Closed", to_status="Open",
                     allowed_roles=["Tester", "Test Lead", "Admin"]),
]


@pytest.mark.parametrize(("status", "role", "allowed"), [
    ("Open", "Admin", ["In Progress"]),
    ("In Progress", "Admin", ["Resolved"]),
    ("Resolved", "Admin", ["Closed", "Open"]),
    ("Closed", "Admin", ["Open"]),
    ("Open", "Tester", []),
    ("Resolved", "Developer", []),
    ("Open", None, []),
])
def test_defect_response_exposes_only_legal_actions(status, role, allowed):
    defect = Defect(id=42, title="Response contract", severity="High",
                    status=status, test_case="TC-003")
    user = User(id=1, username="u", role=role) if role else None
    assert defect_out(defect, RULES, user) == {
        "id": 42, "title": "Response contract", "severity": "High",
        "status": status, "test_case": "TC-003", "allowed": allowed,
    }


def test_defect_creation_defaults_support_an_unlinked_case():
    body = DefectCreate(title="Standalone defect")
    assert body.severity == "Medium"
    assert body.test_case is None
