# SDS-06: Agile Test and Defect Tracking System

İstanbul Kültür Üniversitesi · Software Development with Standards dersi dönem projesi.

ISO/IEC/IEEE 12207 yaşam döngüsü süreç modeline dayalı bir test yönetimi ve defect
takip platformu. Test planlama, test vakası yazımı, defect yaşam döngüsü ve sürüm
yayınlama adımlarını tek yerde yönetir; IEEE 829 dokümanlarını ISO/IEC/IEEE 29119-2
(test süreçleri) ve 29119-3 (test dokümantasyonu) eşlemesiyle üretmeyi hedefler.

> ⚠️ Proje geliştirme aşamasındadır. Demo kullanıcıların parolaları herkese açıktır;
> bu yapılandırma yalnızca yerel demo içindir, üretim için uygun değildir.

## Ekran görüntüleri

**Panel, grafikli metrikler ve sürüm çıkış kapısı:** özet metrik kartları, koşum başına
yığılmış sonuç dağılımı ve başarı trendi, defect burn-up, önem dağılımı, sürüm çıkış
kapısı eşikleri / Test Lead muafiyeti, test vakaları ve yalnızca API'nin izin verdiği
durum geçişleri.

![Panel ve defect takibi](docs/screenshots/dashboard-2x.png)

**Test vakası ve suite yönetimi (`/test-cases`):** kararlı anahtar, test adımları,
beklenen sonuç, öncelik, otomasyon bayrağı, test suite ataması ve zorunlu gereksinim
bağlantıları.

![Test vakası ve suite yönetimi](docs/screenshots/test-cases-2x.png)

**Etkileşimli gereksinim – test izlenebilirlik matrisi (`/test-cases`):** çoka çok
gereksinim ↔ test vakası bağlantıları, kapsam özeti ve kapsam eksikliği (gap) uyarısı.

![Gereksinim – test izlenebilirlik matrisi](docs/screenshots/traceability-matrix-2x.png)

**Test koşumu yürütme ve koşum geçmişi (`/test-runs`):** `Passed` / `Failed` /
`Blocked` / `Skipped` sonuç kaydı, başarısız yürütmeden doğrudan defect açma ve
koşum geçmişi.

![Test koşumu yürütme ekranı](docs/screenshots/test-runs-2x.png)

**Defect detayı (IEEE 829 Test Incident Report):** bağlı test vakası, izin verilen
geçişler ve değiştirilemez geçmiş zaman çizelgesi.

![Defect detay sayfası](docs/screenshots/defect-detail-2x.png)

**Projeler, sürümler ve gereksinimler (`/projects`):** proje/sürüm kataloğu ve
test vakası ↔ gereksinim izlenebilirliği.

![Projeler ve gereksinimler](docs/screenshots/projects-2x.png)

| Giriş ekranı | REST API (Swagger) |
| --- | --- |
| ![Giriş ekranı](docs/screenshots/login-2x.png) | ![API dokümanı](docs/screenshots/api-docs-2x.png) |

## Özellikler

| Özellik | Gereksinim | Standart |
| --- | --- | --- |
| Defect yaşam döngüsü `Open → In Progress → Resolved → Closed` (+ Reopen); geçiş kuralları ve rol kısıtları veritabanında (`defect_transitions`), geçersiz geçiş 409, yetkisiz rol 403 | R4 | 12207 Problem Çözümleme; 29119-2 Test Olay Raporlama |
| Değiştirilemez defect geçmişi (`defect_history`, PostgreSQL trigger ile yalnızca ekleme) | R4, R8 | 12207 Konfigürasyon Yönetimi |
| JWT ile giriş ve rol tabanlı erişim: Admin, Test Lead, Tester, Developer | R8 | 12207 Uygulama |
| Proje, sürüm ve gereksinim yönetimi; test vakası ↔ gereksinim izlenebilirliği (çoka çok) | R2, R7 | 29119-2 Test Tasarımı ve Gerçekleştirme |
| Test vakası (adımlar, beklenen sonuç, öncelik, otomasyon bayrağı, kararlı anahtar) ve test suite CRUD API'si | R2 | 29119-2 Test Tasarımı ve Gerçekleştirme; 29119-3 Test Case Specification |
| Test vakası / suite yönetimi (`/test-cases`) ve etkileşimli gereksinim – test izlenebilirlik matrisi | R2 | 29119-2 Test Tasarımı ve Gerçekleştirme |
| Test koşumu yürütme ekranı (`/test-runs`): `Passed`/`Failed`/`Blocked`/`Skipped` sonuç girme, başarısız yürütmeden defect açma ve koşum geçmişi | R2, R4 | 29119-2 Test Yürütme; Test Olay Raporlama |
| Grafikli metrik paneli (`/`) ve sürüm çıkış kapısı kartı: koşum başına yığılmış sonuç çubuğu + başarı trendi, defect burn-up, önem dağılımı, yapılandırılabilir çıkış eşikleri ve Test Lead muafiyeti | R5, R7 | 29119-2 Test İzleme ve Kontrol |
| Test vakası listesi ve metrikler: koşum oranı, başarı oranı, açık defect sayısı | R2, R5 | 29119-2 Test İzleme ve Kontrol |
| JUnit XML içe aktarımı; commit/branch üst verisi, projeye göre kararlı test vakası eşleme ve eşleşmeyen sonuç raporu | R6 | 29119-2 Test Yürütme; 12207 Doğrulama |
| Cobertura XML satır/dal kapsamı içe aktarımı ve GitHub Actions CI kanıtlarının geçici örneğe otomatik aktarımı | R5, R6 | 29119-2 Test İzleme ve Kontrol; 12207 Doğrulama |
| Test koşumu (Test Run) ve test yürütme (Test Execution): Passed / Failed / Blocked / Skipped sonuçları, yürütme ↔ defect bağlantısı ve `Resolved → Closed` doğrulama şartı | R2, R4 | 29119-2 Test Yürütme; 12207 Doğrulama |
| Sürüm durumları (`Planned`, `In Test`, `Ready`, `Released`), yapılandırılabilir çıkış kriterleri (başarı oranı, açık kritik defect, gereksinim kapsama) ve Test Lead / Admin muafiyet kaydı | R7 | 29119-2 Test Tamamlama; 12207 Kalite Güvence |
| IEEE 829 Test Plan kaydı (`Draft` / `In Review` / `Approved`), anlık görüntü (snapshot) saklama ve Jinja2 + WeasyPrint/PDF + HTML üretimi | R1, R3 | IEEE 829 Test Plan; 29119-3 Test Plan; 12207 Uygulama |

**Planlanan:** genişletilmiş metrik SQL agregasyon API'si (PLN-24) ve
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

## JUnit XML içe aktarımı (PLN-22 — Esra Kaya)

`POST /api/projects/{id}/runs/import`, ham XML gövdesini `application/xml` olarak
alır; Admin, Test Lead veya Tester token'ı gerekir. `commit` ve `branch` sorgu
parametreleriyle üst veri saklanır. `test_case_id` özelliği (yoksa tam testcase adı),
projenin gereksinimlerine bağlı test vakalarıyla eşlenir; eşleşmeyen sonuçlar da
kaydedilip ayrı raporlanır. Sınır 1 MiB / 5000 sonuçtur.

İçe aktarım anlık görüntüleri genel PLN-17 koşum yönetiminden ayrıdır; mevcut test
vakası durumlarını veya metrikleri güncellemez. Okuma uçları, örnek XML, eşleme
kuralları ve migrasyon ayrıntıları: [JUnit import sözleşmesi](docs/junit-import.md).

## Cobertura içe aktarımı ve CI aktarımı (PLN-23 — Esra Kaya)

`POST /api/projects/{id}/coverage/import`, Cobertura XML satır/dal kapsamını
saklar; sonuçlar listelenebilir ve tekrar okunabilir. İsteğe bağlı JUnit içe
aktarım kimliğiyle commit/branch kanıtı ilişkilendirilir. CI kendi gerçek JUnit ve
Cobertura raporlarını geçici bir SDS-06 örneğine aktarır; sonuçlar **Artifacts →
ci-import-evidence** altında 14 gün saklanır. Canlı proje veritabanına yazılmaz.
Sınırlar, doğrulama, API ve migrasyon: [Cobertura sözleşmesi](docs/cobertura-import.md).

## Performans ve birim test kapsamı (PLN-35)

10.000 yürütmeyle gerçek tarayıcı panel süresi ve Test Plan üretimi ölçülür.
İş akışı/metrik modüllerinin her birinde satır ve dal birim test kapsamı en az
%80 olmalıdır. [Çalıştırma yönergesi](quality/README.md) ·
[Ölçüm raporu ve ISO/IEC 25010 girdileri](docs/pln35-quality-measurements.md).

## SQL metrikleri (PLN-24 — Esra Kaya)

`GET /api/metrics/expanded`: proje/sürüm ve UTC tarih aralığına göre koşum
başarı oranı, gereksinim kapsamı, yeniden açılma oranı, defect yaşı ve ilk çözüm
süresi. Eski `/api/metrics` sözleşmesi korunur. Sprint modeli bulunmadığından
sprint kimliğiyle filtreleme mevcut değildir; bilinen sprint tarih aralığı
kullanılabilir. Formüller ve kapsam: [Metrik API sözleşmesi](docs/metrics-api.md).

## Dokümanlar

| Doküman | Dosya |
| --- | --- |
| Yazılım Gereksinim Spesifikasyonu (R1–R8) | [docs/srs.md](docs/srs.md) |
| Gereksinim İzlenebilirlik Matrisi (RTM v1) | [docs/requirements-traceability-matrix-v1.md](docs/requirements-traceability-matrix-v1.md) |
| Metrik Tanımları Kataloğu | [docs/metric-definitions.md](docs/metric-definitions.md) |
| Proje Planı | [docs/project-plan.md](docs/project-plan.md) |
| Test Plan (IEEE 829 / 29119-3) | [docs/test-plan.md](docs/test-plan.md) |
| İş Akışı Test Vakası Spesifikasyonu (IEEE 829) · Ara Demo Senaryosu | [docs/test-case-specification-workflow.md](docs/test-case-specification-workflow.md) · [docs/mid-period-demo-scenario.md](docs/mid-period-demo-scenario.md) |
| Yazılım Tasarım Tanımı (mimari ve veri modeli) | [docs/software-design-description.md](docs/software-design-description.md) |
| Standart durumu ve IEEE 829 ↔ 29119 eşlemesi | [docs/standard-status-and-mapping.md](docs/standard-status-and-mapping.md) |
| Risk kaydı · Definition of Done | [docs/risk-register.md](docs/risk-register.md) · [docs/definition-of-done.md](docs/definition-of-done.md) |

## Katkı süreci

`main` korumalıdır. Her iş plan maddesini taşıyan bir branch'te yapılır
(`feature/pln-xx-kisa-ad`) ve en az bir onaylı Pull Request ile birleştirilir. PR
açıklaması `.github/pull_request_template.md` bölümlerini ve bir `Agent:` satırını
içermelidir; `PR description` CI kontrolü bunu denetler. Ajan kuralları:
[AGENTS.md](AGENTS.md).
