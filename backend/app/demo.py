"""Demo modu (PLN-38): demo hesapları, demo verisi ve gece sıfırlaması.

DEMO_MODE=1 değilse hiçbir şey eklenmez; kurulum boş gelir ve ilk Admin hesabı
ADMIN_USERNAME/ADMIN_PASSWORD ile açılır. Demo verisi önceden migration'lardaydı (0001, 0002,
0004); demo dışı kurulumlar boş gelsin diye buraya taşındı.
"""
import os
import sys

import bcrypt
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .db import SessionLocal, engine
from .models import (
    Defect,
    DefectHistory,
    Project,
    Requirement,
    TestCase,
    User,
    project_members,
)

DEMO_PASSWORD = "demo1234"
# bcrypt("demo1234"); eski 0002 migration'ındaki değerle aynı, mevcut demo tokenları bozulmaz.
DEMO_HASH = "$2b$12$SprgTF7gPXa1GnXin3t49.S5LO2udixOI8mEKMn/mBKaPlRbh1VnK"
DEMO_USERS = [("admin", "Admin"), ("testlead", "Test Lead"), ("tester", "Tester"),
              ("developer", "Developer")]
DEMO_CASES = [
    ("TC-001", "Kullanıcı girişi başarılı", "R1", "Passed"),
    ("TC-002", "Hatalı şifre ile giriş reddedilir", "R1", "Passed"),
    ("TC-003", "Defect oluşturma formu", "R3", "Failed"),
    ("TC-004", "Defect durum geçişi kuralları", "R4", "Passed"),
    ("TC-005", "Test özet raporu üretimi", "R6", "Not Run"),
    ("TC-006", "JUnit sonuç içe aktarımı", "R7", "Blocked"),
]
# main.require_verification_passed, defect #3 / TC-005 için belgelenmiş bir istisna içerir.
DEMO_DEFECTS = [
    (1, "Defect formu boş başlığı kabul ediyor", "High", "Open", "TC-003"),
    (2, "Dashboard grafiği yavaş yükleniyor", "Medium", "In Progress", None),
    (3, "PDF raporunda Türkçe karakter sorunu", "Low", "Resolved", "TC-005"),
]


def demo_mode() -> bool:
    return os.getenv("DEMO_MODE") == "1"


def seed_demo(db: Session) -> None:
    project = Project(name="SDS-06", description="")
    db.add(project)
    db.flush()
    requirements = {f"R{n}": Requirement(id=f"R{n}", project_id=project.id,
                                         title=f"Gereksinim R{n}", description="")
                    for n in range(1, 9)}
    db.add_all(requirements.values())
    db.add_all(TestCase(id=key, title=title, requirement=req, status=status,
                        requirements=[requirements[req]]) for key, title, req, status in DEMO_CASES)
    users = [User(username=name, role=role, password_hash=DEMO_HASH) for name, role in DEMO_USERS]
    db.add_all(users)
    db.flush()
    for defect_id, title, severity, status, case in DEMO_DEFECTS:
        db.add(Defect(id=defect_id, title=title, severity=severity, status=status, test_case=case))
        db.flush()
        db.add(DefectHistory(defect_id=defect_id, from_status=None, to_status=status))
    db.execute(project_members.insert(), [{"project_id": project.id, "user_id": u.id}
                                           for u in users if u.role in ("Tester", "Developer")])
    if db.get_bind().dialect.name == "postgresql":
        # Elle verilen defect id'lerinden sonra sequence'i ilerlet.
        db.execute(text("SELECT setval('defects_id_seq', (SELECT MAX(id) FROM defects))"))


def bootstrap() -> None:
    """Migration'lardan sonra çağrılır: demo verisini veya ilk Admin hesabını ekler."""
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(User)):
            return
        if demo_mode():
            seed_demo(db)
        elif os.getenv("ADMIN_USERNAME") and os.getenv("ADMIN_PASSWORD"):
            password = os.environ["ADMIN_PASSWORD"].encode()
            if len(password) < 8 or len(password) > 72:
                raise SystemExit("ADMIN_PASSWORD 8-72 bayt olmalıdır")
            db.add(User(username=os.environ["ADMIN_USERNAME"], role="Admin",
                        password_hash=bcrypt.hashpw(password, bcrypt.gensalt()).decode()))
        db.commit()


def reset() -> None:
    """Demo veritabanını silip yeniden kurar. Yalnızca DEMO_MODE=1 iken çalışır."""
    if not demo_mode():
        raise SystemExit("Sıfırlama yalnızca DEMO_MODE=1 iken çalışır")
    from alembic import command
    from alembic.config import Config

    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")  # env.py, head'e ulaşınca bootstrap() çağırır
    engine.dispose()


if __name__ == "__main__":
    if sys.argv[1:] != ["reset"]:
        raise SystemExit("Kullanım: python -m app.demo reset")
    reset()
