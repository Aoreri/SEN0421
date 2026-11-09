# SDS-06: Agile Test and Defect Tracking System

> ⚠️ **Bu repo şu an bir DEMO / TEMPLATE'tir.** Proje iskeletini ve temel akışı göstermek için hazırlanmıştır;
> veriler PostgreSQL'de tutulur; demo kullanıcılar ve parolaları herkese açıktır, üretim için uygun değildir.

İstanbul Kültür Üniversitesi · Software Development with Standards dersi projesi.
ISO/IEC/IEEE 12207 yaşam döngüsü süreç modeline dayalı; IEEE 829 ve ISO/IEC/IEEE 29119-2 / 29119-3 referans alınır.

## Yapı

```
backend/    FastAPI REST API (test vakaları, defect'ler, yaşam döngüsü, metrikler)
frontend/   React + TypeScript (Vite) arayüz
```

## Çalıştırma

**Veritabanı** (PostgreSQL 16, Docker gerekir)

```bash
docker compose up -d db
```

**Backend** (http://localhost:8000, API dokümanı: `/docs`)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head          # şemayı oluşturur + demo tohum verisini yükler
uvicorn app.main:app --reload
pytest                        # testler (varsayılan: geçici SQLite)
```

**Demo kullanıcılar** (hepsinin parolası `demo1234`; API sözleşmesi: [docs/api-auth.md](docs/api-auth.md))

| Kullanıcı | Rol |
| --- | --- |
| `admin` | Admin |
| `testlead` | Test Lead |
| `tester` | Tester |
| `developer` | Developer |

Bağlantı adresi `DATABASE_URL` ortam değişkeninden okunur
(varsayılan `postgresql+psycopg://sds06:sds06@localhost:5432/sds06`).
JWT imza anahtarı `JWT_SECRET` ortam değişkeninden okunur; verilmezse her başlatmada rastgele üretilir.
Yeni migrasyon: `alembic revision -m "açıklama"`.

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
- JWT ile giriş ve rol tabanlı erişim (Admin, Test Lead, Tester, Developer)
- Basit metrikler: koşum oranı, başarı oranı, açık defect sayısı

## Planlanan (template sonrası)

- IEEE 829 test planı / test özet raporu üretimi (Jinja2 + WeasyPrint)
- JUnit / Cobertura sonuç içe aktarımı, CI/CD, Docker Compose

## PLN-11 — Sürekli entegrasyon (Esra Kaya)

GitHub Actions `CI` hattı, `main` dalına push yapıldığında,
her pull request açılışında/güncellemesinde ve Actions ekranından elle çalışır.
İki bağımsız iş bulunur; başarısız bir komut ilgili işi başarısız yapar:

- **Backend checks:** Python 3.12, Ruff lint, mypy tip denetimi ve pytest.
- **Frontend checks:** Node.js 22, ESLint, TypeScript tip denetimi ve Vite üretim derlemesi.

Yerelde aynı kontroller:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
ruff check .
mypy app
python -m pytest -q
```

Ayrı terminalde:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run build
```

Başlangıç API testleri sağlık kontrolünü, defect oluşturmayı, boş başlık reddini,
geçerli/geçersiz durum geçişlerini, geçmişin korunmasını, bulunamayan defect'i
ve örnek metrikleri kapsar. Testler varsayılan olarak geçici bir SQLite veritabanında çalışır (Alembic migrasyonlarıyla kurulur);
`DATABASE_URL` verilirse o veritabanını kullanır.
Bu aşamada frontend için lint, tip kontrolü ve derleme çalışır; frontend birim
test altyapısı henüz eklenmemiştir. Genişletilmiş testler ve Cobertura raporu
PLN-13 kapsamındadır. Sonuçlar GitHub → Actions → CI ekranından izlenebilir.
Bu hat branch koruma kurallarını kendiliğinden etkinleştirmez.
