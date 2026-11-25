"""PLN-33: atomically create or reuse an incident for a matched JUnit failure."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .junit import JUnitResult
from .models import Defect, DefectHistory, JUnitAutoDefect


def failure_defect(db: Session, project_id: int, test_case_id: str, result: JUnitResult) -> int:
    if result.status != "Failed" or result.failure_signature is None:
        raise ValueError("Only failed JUnit results can create an automatic defect")
    lookup = select(JUnitAutoDefect.defect_id).where(
        JUnitAutoDefect.project_id == project_id,
        JUnitAutoDefect.test_case_id == test_case_id,
        JUnitAutoDefect.failure_signature == result.failure_signature,
    )
    existing = db.scalar(lookup)
    if existing is not None:
        return existing
    try:
        # If another import wins the unique key, rollback the tentative defect as
        # well as its key. The enclosing import transaction remains intact.
        with db.begin_nested():
            title = f"JUnit {test_case_id}: {result.name}"[:200]
            defect = Defect(title=title, severity="Medium", status="Open", test_case=test_case_id)
            db.add(defect)
            db.flush()
            db.add(JUnitAutoDefect(project_id=project_id, test_case_id=test_case_id,
                                  failure_signature=result.failure_signature, defect_id=defect.id))
            db.flush()
            db.add(DefectHistory(defect_id=defect.id, from_status=None, to_status="Open"))
        return defect.id
    except IntegrityError:
        # PostgreSQL's default READ COMMITTED sees the competing committed key.
        existing = db.scalar(lookup)
        if existing is None:
            raise
        return existing
