# SDS-06: Agile Test and Defect Tracking System

> ⚠️ **Bu repo şu an bir DEMO / TEMPLATE'tir.** Proje iskeletini ve temel akışı göstermek için hazırlanmıştır;
> veriler PostgreSQL'de tutulur ancak kimlik doğrulama henüz yoktur; üretim için uygun değildir.

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

### Docker Compose ile tek komut (PLN-12 — Esra Kaya)

Docker Engine / Docker Desktop ve Docker Compose v2 gerekir. Proje kökünde:

```bash
docker compose up --build -d --wait
```

Bu komut PostgreSQL 16'yı, FastAPI backend'ini ve derlenmiş React arayüzünü
birlikte başlatır. Veritabanı hazır olduktan sonra backend mevcut Alembic
migrasyonlarını (`alembic upgrade head`) uygular; migrasyon başarısızsa API
başlamaz. İlk migrasyon demo verisini yükler, sonraki başlangıçlar mevcut
veriyi sıfırlamaz. Frontend backend sağlıklı olduktan sonra başlar.

- Arayüz: http://localhost:5173 (Nginx ile sunulan derlenmiş sürüm; hot reload yok).
- API / Swagger: http://localhost:8000/docs; sağlık kontrolü: http://localhost:8000/api/health.
- Arayüzün `/api/` istekleri Nginx üzerinden `backend:8000` adresine gider.
- Backend `DATABASE_URL` ile Compose ağındaki `db:5432` PostgreSQL servisine bağlanır.
- Host üzerindeki PostgreSQL erişimi ve yerel geliştirme adresi değişmez: `localhost:5432`.

```bash
docker compose ps                   # servis ve sağlık durumları
docker compose logs backend         # migrasyon ve API logları
docker compose down                 # durdurur; pgdata verisini korur
docker compose up -d --wait          # mevcut imajlarla yeniden başlatır
```

`pgdata` adlı mevcut volume kullanılır. `docker compose down -v` veritabanını
siler; yalnızca atılabilir demo verisini sıfırlamak istediğinizde kullanın.
5432, 8000 ve 5173 portları boş olmalı; yerelde çalışan aynı servisleri önce
durdurun. Kimlik doğrulaması yoktur ve `sds06` şifresi yalnızca yerel demo içindir;
bu yapılandırma üretim dağıtımı için değildir.

Bu çalışma PLN-12 / ISO/IEC/IEEE 12207 — Konfigürasyon Yönetimi kapsamındadır.
API, veri modeli, migrasyonlar ve mevcut frontend geliştirme akışı değiştirilmez.

### Docker dışında yerel geliştirme

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

Bağlantı adresi `DATABASE_URL` ortam değişkeninden okunur
(varsayılan `postgresql+psycopg://sds06:sds06@localhost:5432/sds06`).
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
- Basit metrikler: koşum oranı, başarı oranı, açık defect sayısı

## Planlanan (template sonrası)

- Kimlik doğrulama ve rol tabanlı erişim
- IEEE 829 test planı / test özet raporu üretimi (Jinja2 + WeasyPrint)
- JUnit / Cobertura sonuç içe aktarımı, CI/CD

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
python -m pytest -q --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml
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
test altyapısı henüz eklenmemiştir. Backend test kapsamı ve Cobertura çıktıları aşağıdaki PLN-13 bölümünde açıklanmıştır. Sonuçlar GitHub → Actions → CI ekranından izlenebilir.
Bu hat branch koruma kurallarını kendiliğinden etkinleştirmez.


## PLN-13 — Backend testleri ve Cobertura kapsam raporu (Esra Kaya)

ISO/IEC/IEEE 29119-2 — Test Uygulama; ISO/IEC/IEEE 12207 — Doğrulama.
Mevcut uygulama davranışları test edilir; yeni API veya veri modeli eklenmez.

- `tests/test_unit.py`: veritabanına bağlanmadan defect yanıtı ve izin verilen
  işlem sözleşmesi (R3/R4) için birim testleri.
- `tests/test_api.py` ve `tests/test_integration.py`: migrasyonlarla kurulan
  veritabanında API, R3 defect oluşturma, R4 yaşam döngüsü, geçmişin korunması,
  test vakası/gereksinim izlenebilirliği ve metriklerin sınır durumları.
- PostgreSQL'e özel testler geçmiş tablosunda UPDATE ve DELETE'in trigger
  tarafından reddedildiğini doğrular. SQLite çalışmasında yalnızca bu testler atlanır.

Backend klasöründe bağımlılıkları `python -m pip install -r requirements-dev.txt`
ile yükleyip çalıştırın:

```bash
python -m pytest -q --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml
python -m pytest -q -m unit
```

İlk komut satır ve dal kapsamını ölçer, Cobertura biçiminde `backend/coverage.xml`
üretir. Yüzde yalnızca `app/` kaynaklarını kapsar; frontend veya migrasyon kapsamı
olarak yorumlanmamalıdır. Rapor dosyaları üretilen çıktılardır; Git'e eklenmez.

Varsayılan çalıştırma geçici SQLite kullanır. PostgreSQL için yalnızca atılabilir,
boş bir test veritabanını `DATABASE_URL` ile açıkça seçin. Her entegrasyon testi
`alembic downgrade base` / `upgrade head` çalıştırır; geliştirme veya gerçek veri
bulunan veritabanını seçmeyin. Salt birim testleri migrasyon çalıştırmaz.

CI'da mevcut **Backend checks** işi SQLite ile çalışır; yeni
**Backend PostgreSQL tests** işi kendine ait PostgreSQL 16 servisini kullanır.
Her ikisi de testlerden sonra Cobertura XML dosyasını yükler (dosya oluşmuşsa,
testler başarısız olduğunda da). GitHub → Actions → ilgili CI çalışması →
**Artifacts** bölümünden `backend-coverage-sqlite` veya
`backend-coverage-postgres` çıktısını indirin. Çıktılar 14 gün saklanır.
