# SDS-06: Agile Test and Defect Tracking System

> ⚠️ **Bu repo şu an bir DEMO / TEMPLATE'tir.** Proje iskeletini ve temel akışı göstermek için hazırlanmıştır;
> veriler bellekte tutulur, kimlik doğrulama yoktur ve üretim için uygun değildir.

İstanbul Kültür Üniversitesi · Software Development with Standards dersi projesi.
ISO/IEC/IEEE 12207 yaşam döngüsü süreç modeline dayalı; IEEE 829 ve ISO/IEC/IEEE 29119-2 / 29119-3 referans alınır.

## Yapı

```
backend/    FastAPI REST API (test vakaları, defect'ler, yaşam döngüsü, metrikler)
frontend/   React + TypeScript (Vite) arayüz
```

## Katkı süreci

`main` korumalıdır: doğrudan push yapılamaz. Her iş için `feature/<plan-id>-kisa-ad` branch'i açın
ve Pull Request gönderin; birleştirme için en az 1 onay gerekir. PR açıklaması
`.github/pull_request_template.md` bölümlerini doldurmalı ve tüm bölümlerden sonra bir `Agent:` satırı içermelidir;
`PR description` CI kontrolü bunu denetler. Ajan kuralları: [AGENTS.md](AGENTS.md).

## Çalıştırma

**Backend** (http://localhost:8000, API dokümanı: `/docs`)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend** (http://localhost:5173, Node.js 18+ gerekir)

```bash
cd frontend
npm install
npm run dev
```

Vite geliştirme sunucusu `/api` isteklerini `http://localhost:8000` adresindeki backend'e yönlendirir.

## Demoda neler var

- Test vakaları listesi (gereksinim eşlemesiyle, R1-R8)
- Defect oluşturma ve yaşam döngüsü: `Open → In Progress → Resolved → Closed` (+ Reopen)
- Geçersiz geçişlerin backend'de reddedilmesi ve değiştirilemez geçmiş kaydı (`/api/defects/{id}/history`)
- Basit metrikler: koşum oranı, başarı oranı, açık defect sayısı

## Planlanan (template sonrası)

- PostgreSQL + Alembic, kimlik doğrulama ve rol tabanlı erişim
- IEEE 829 test planı / test özet raporu üretimi (Jinja2 + WeasyPrint)
- JUnit / Cobertura sonuç içe aktarımı, CI/CD, Docker Compose
