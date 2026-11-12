# SDS-06: Agile Test and Defect Tracking System

İstanbul Kültür Üniversitesi · Software Development with Standards dersi dönem projesi.

ISO/IEC/IEEE 12207 yaşam döngüsü süreç modeline dayalı bir test yönetimi ve defect
takip platformu. Test planlama, test vakası yazımı, defect yaşam döngüsü ve sürüm
yayınlama adımlarını tek yerde yönetir; IEEE 829 dokümanlarını ISO/IEC/IEEE 29119-2
(test süreçleri) ve 29119-3 (test dokümantasyonu) eşlemesiyle üretmeyi hedefler.

> ⚠️ Proje geliştirme aşamasındadır. Demo kullanıcıların parolaları herkese açıktır;
> bu yapılandırma yalnızca yerel demo içindir, üretim için uygun değildir.

## Ekran görüntüleri

**Panel ve defect takibi:** metrik kartları, gereksinime bağlı test vakaları, defect
oluşturma ve yalnızca API'nin izin verdiği durum geçişleri.

![Panel ve defect takibi](docs/screenshots/dashboard.png)

**Defect detayı (IEEE 829 Test Incident Report):** bağlı test vakası, izin verilen
geçişler ve değiştirilemez geçmiş zaman çizelgesi.

![Defect detay sayfası](docs/screenshots/defect-detail.png)

**Projeler, sürümler ve gereksinimler:** test vakası ↔ gereksinim izlenebilirliği.

![Projeler ve gereksinimler](docs/screenshots/projects.png)

| Giriş ekranı | REST API (Swagger) |
| --- | --- |
| ![Giriş ekranı](docs/screenshots/login.png) | ![API dokümanı](docs/screenshots/api-docs.png) |

## Özellikler

| Özellik | Gereksinim | Standart |
| --- | --- | --- |
| Defect yaşam döngüsü `Open → In Progress → Resolved → Closed` (+ Reopen); geçiş kuralları ve rol kısıtları veritabanında (`defect_transitions`), geçersiz geçiş 409, yetkisiz rol 403 | R4 | 12207 Problem Çözümleme; 29119-2 Test Olay Raporlama |
| Değiştirilemez defect geçmişi (`defect_history`, PostgreSQL trigger ile yalnızca ekleme) | R4, R8 | 12207 Konfigürasyon Yönetimi |
| JWT ile giriş ve rol tabanlı erişim: Admin, Test Lead, Tester, Developer | R8 | 12207 Uygulama |
| Proje, sürüm ve gereksinim yönetimi; test vakası ↔ gereksinim izlenebilirliği (çoka çok) | R2, R7 | 29119-2 Test Tasarımı ve Gerçekleştirme |
| Test vakası listesi ve metrikler: koşum oranı, başarı oranı, açık defect sayısı | R2, R5 | 29119-2 Test İzleme ve Kontrol |

**Planlanan:** test vakası / suite yönetimi, test koşumları, JUnit XML ve Cobertura
içe aktarımı, grafikli metrik paneli, sürüm çıkış kriterleri ve IEEE 829 Test Plan /
Test Summary Report / Test Incident Report üretimi (Jinja2 + WeasyPrint).

## Mimari

```
frontend/   React + TypeScript (Vite); tüm API çağrıları src/api.ts üzerinden
backend/    FastAPI REST API; SQLAlchemy modelleri app/models.py, Alembic migrasyonları alembic/versions/
docs/       SRS, proje planı, Test Plan, SDD, risk kaydı, standart eşlemesi
docker-compose.yml   PostgreSQL 16 + backend + frontend
```

## Çalıştırma

### Docker Compose (önerilen)

Docker Desktop / Docker Engine ve Compose v2 gerekir. 5432, 8000 ve 5173 portları boş olmalıdır.

```bash
docker compose up --build -d --wait
```

- Arayüz: http://localhost:5173
- API / Swagger: http://localhost:8000/docs · sağlık kontrolü: http://localhost:8000/api/health

Backend açılışta `alembic upgrade head` çalıştırır; ilk migrasyon demo verisini yükler.
`docker compose down` veriyi korur, `docker compose down -v` demo veritabanını siler.

### Yerel geliştirme

```bash
docker compose up -d db                      # yalnızca PostgreSQL

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head                         # şema + demo verisi
uvicorn app.main:app --reload                # http://localhost:8000

cd frontend
npm install
npm run dev                                  # http://localhost:5173, /api → :8000
```

Ortam değişkenleri: `DATABASE_URL` (varsayılan
`postgresql+psycopg://sds06:sds06@localhost:5432/sds06`), `JWT_SECRET` (verilmezse her
başlatmada rastgele üretilir).

### Demo kullanıcılar

Hepsinin parolası `demo1234`. API sözleşmesi: [docs/api-auth.md](docs/api-auth.md).

| Kullanıcı | Rol |
| --- | --- |
| `admin` | Admin |
| `testlead` | Test Lead |
| `tester` | Tester |
| `developer` | Developer |

## Testler ve CI

```bash
cd backend && ruff check . && mypy app && python -m pytest -q --cov=app --cov-report=xml:coverage.xml
cd frontend && npm run lint && npm run typecheck && npm run build
```

Testler varsayılan olarak geçici bir SQLite veritabanında çalışır. PostgreSQL'e özgü
testler (geçmiş tablosunda UPDATE/DELETE'in trigger ile reddi) için yalnızca atılabilir
bir test veritabanını `DATABASE_URL` ile verin; entegrasyon testleri şemayı sıfırlar.

GitHub Actions `CI` hattı her PR'da backend (SQLite ve PostgreSQL 16) ve frontend
kontrollerini çalıştırır; Cobertura kapsam raporları Actions → **Artifacts** altında
14 gün saklanır.

## Dokümanlar

| Doküman | Dosya |
| --- | --- |
| Yazılım Gereksinim Spesifikasyonu (R1–R8) | [docs/srs.md](docs/srs.md) |
| Proje Planı | [docs/project-plan.md](docs/project-plan.md) |
| Test Plan (IEEE 829 / 29119-3) | [docs/test-plan.md](docs/test-plan.md) |
| Yazılım Tasarım Tanımı (mimari ve veri modeli) | [docs/software-design-description.md](docs/software-design-description.md) |
| Standart durumu ve IEEE 829 ↔ 29119 eşlemesi | [docs/standard-status-and-mapping.md](docs/standard-status-and-mapping.md) |
| Risk kaydı · Definition of Done | [docs/risk-register.md](docs/risk-register.md) · [docs/definition-of-done.md](docs/definition-of-done.md) |

## Katkı süreci

`main` korumalıdır. Her iş plan maddesini taşıyan bir branch'te yapılır
(`feature/pln-xx-kisa-ad`) ve en az bir onaylı Pull Request ile birleştirilir. PR
açıklaması `.github/pull_request_template.md` bölümlerini ve bir `Agent:` satırını
içermelidir; `PR description` CI kontrolü bunu denetler. Ajan kuralları:
[AGENTS.md](AGENTS.md).

## Ekip

| Üye | Rol |
| --- | --- |
| Caner Serbest | Backend lideri |
| Emirhan Canarslan | Frontend lideri |
| Esra Kaya | QA ve DevOps |
| Emirhan Ulutürk | Ürün sahibi / gereksinim ve dokümantasyon |
