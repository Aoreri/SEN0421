"""SDS-06 Agile Test and Defect Tracking System - DEMO / TEMPLATE backend.

Bu dosya yalnızca bir şablondur: veriler bellekte tutulur, kimlik doğrulama yoktur.
Gerçek sürümde PostgreSQL, rol tabanlı erişim ve Alembic migrasyonları kullanılacaktır.
"""

from datetime import datetime, timezone
from typing import TypedDict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="SDS-06 Test & Defect Tracker (Template)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Defect yaşam döngüsü (WP-04): izin verilen geçişler
TRANSITIONS = {
    "Open": ["In Progress"],
    "In Progress": ["Resolved"],
    "Resolved": ["Closed", "Open"],  # Resolved -> Open = Reopen
    "Closed": ["Open"],  # Closed -> Open = Reopen
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Örnek (tohum) veri -------------------------------------------------------
TEST_CASES = [
    {"id": "TC-001", "title": "Kullanıcı girişi başarılı", "requirement": "R1", "status": "Passed"},
    {"id": "TC-002", "title": "Hatalı şifre ile giriş reddedilir", "requirement": "R1", "status": "Passed"},
    {"id": "TC-003", "title": "Defect oluşturma formu", "requirement": "R3", "status": "Failed"},
    {"id": "TC-004", "title": "Defect durum geçişi kuralları", "requirement": "R4", "status": "Passed"},
    {"id": "TC-005", "title": "Test özet raporu üretimi", "requirement": "R6", "status": "Not Run"},
    {"id": "TC-006", "title": "JUnit sonuç içe aktarımı", "requirement": "R7", "status": "Blocked"},
]

class DefectRecord(TypedDict):
    id: int
    title: str
    severity: str
    status: str
    test_case: str | None


DEFECTS: dict[int, DefectRecord] = {
    1: {"id": 1, "title": "Defect formu boş başlığı kabul ediyor", "severity": "High",
        "status": "Open", "test_case": "TC-003"},
    2: {"id": 2, "title": "Dashboard grafiği yavaş yükleniyor", "severity": "Medium",
        "status": "In Progress", "test_case": None},
    3: {"id": 3, "title": "PDF raporunda Türkçe karakter sorunu", "severity": "Low",
        "status": "Resolved", "test_case": "TC-005"},
}

# Değiştirilemez geçmiş kaydı: yalnızca ekleme yapılır
HISTORY = [
    {"defect_id": d["id"], "from": None, "to": d["status"], "at": now()} for d in DEFECTS.values()
]


# --- Şemalar ------------------------------------------------------------------
class DefectCreate(BaseModel):
    title: str
    severity: str = "Medium"
    test_case: str | None = None


class Transition(BaseModel):
    to: str


# --- Uç noktalar --------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "template": True}


@app.get("/api/test-cases")
def list_test_cases():
    return TEST_CASES


@app.get("/api/defects")
def list_defects():
    return [{**d, "allowed": TRANSITIONS[d["status"]]} for d in DEFECTS.values()]


@app.post("/api/defects", status_code=201)
def create_defect(body: DefectCreate):
    if not body.title.strip():
        raise HTTPException(422, "Başlık boş olamaz")
    new_id = max(DEFECTS, default=0) + 1
    DEFECTS[new_id] = {
        "id": new_id,
        "status": "Open",
        "title": body.title,
        "severity": body.severity,
        "test_case": body.test_case,
    }
    HISTORY.append({"defect_id": new_id, "from": None, "to": "Open", "at": now()})
    return DEFECTS[new_id]


@app.post("/api/defects/{defect_id}/transition")
def transition_defect(defect_id: int, body: Transition):
    defect = DEFECTS.get(defect_id)
    if not defect:
        raise HTTPException(404, "Defect bulunamadı")
    if body.to not in TRANSITIONS[defect["status"]]:
        raise HTTPException(400, f"Geçersiz geçiş: {defect['status']} -> {body.to}")
    HISTORY.append({"defect_id": defect_id, "from": defect["status"], "to": body.to, "at": now()})
    defect["status"] = body.to
    return defect


@app.get("/api/defects/{defect_id}/history")
def defect_history(defect_id: int):
    return [h for h in HISTORY if h["defect_id"] == defect_id]


@app.get("/api/metrics")
def metrics():
    total = len(TEST_CASES)
    executed = [t for t in TEST_CASES if t["status"] in ("Passed", "Failed")]
    passed = sum(t["status"] == "Passed" for t in TEST_CASES)
    open_defects = sum(d["status"] != "Closed" for d in DEFECTS.values())
    return {
        "total_tests": total,
        "execution_rate": round(len(executed) / total * 100, 1) if total else 0,
        "pass_rate": round(passed / len(executed) * 100, 1) if executed else 0,
        "open_defects": open_defects,
    }
