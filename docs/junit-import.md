# PLN-22 — JUnit XML içe aktarımı (Esra Kaya)

**Hedef:** 16.11.2026 · **Gereksinim:** R6
**Standart:** ISO/IEC/IEEE 29119-2 — Test Yürütme; ISO/IEC/IEEE 12207 — Doğrulama.

## API sözleşmesi

`POST /api/projects/{project_id}/runs/import` mevcut bir projeye JUnit XML sonuçlarını
tek işlemde kaydeder ve `201` döner. Gövde **ham XML** olmalıdır; JSON veya multipart
form değildir. `Content-Type: application/xml` veya `text/xml` kullanılır.
Kimlik doğrulaması gerekir; Admin, Test Lead ve Tester içe aktarabilir. Developer
salt okuma yapabilir. Proje yetkileri mevcut uygulamadaki genel rol modelini izler;
bu değişiklik ayrı bir proje üyeliği/yetkilendirme sistemi eklemez.

İsteğe bağlı sorgu parametreleri:

- `commit`: 7–64 hexadecimal karakterlik Git commit kimliği.
- `branch`: en fazla 255 karakter; boş veya kontrol karakteri içeremez.

Bu üst veriler içe aktarım kaydında saklanır; XML içindeki `properties` alanından
üst veri okunmaz. API GitHub'a bağlanıp commit/branch'in gerçekten varlığını doğrulamaz.

Örnek `junit.xml`:

```xml
<testsuites>
  <testsuite name="backend">
    <testcase name="test_login" classname="tests.auth" time="0.12">
      <properties>
        <property name="test_case_id" value="TC-001"/>
      </properties>
    </testcase>
    <testcase name="TC-003"><failure message="Expected 201">Actual 500</failure></testcase>
    <testcase name="TC-005"><skipped message="Not selected"/></testcase>
    <testcase name="unknown_test"><error message="Setup error"/></testcase>
  </testsuite>
</testsuites>
```

```bash
curl -X POST 'http://localhost:8000/api/projects/1/runs/import?commit=abcdef1&branch=main' \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'Content-Type: application/xml' \
  --data-binary @junit.xml
```

`<TOKEN>`, mevcut `/api/auth/login` yanıtındaki `access_token` ile değiştirilir.
Örnekteki anahtarlar projenin test vakalarıyla bağlıysa `summary`:

```json
{"total": 4, "matched": 3, "unmatched": 1, "passed": 1, "failed": 2, "skipped": 1}
```

Yanıt ayrıca `id`, `project_id`, `imported_by`, `commit`, `branch`, `created_at`,
`results` ve `unmatched_results` içerir. Her sonuçta sıra (`position`, 0'dan başlar),
JUnit adı/sınıfı/suite'i, bildirilen anahtar, eşleşen `test_case_id`, sonuç, süre,
tanı mesajı ve varsa eşleşmeme nedeni bulunur. Özet tüm sonuçları kapsar;
başarı/başarısızlık sayıları yalnızca eşleşenlerle sınırlı değildir.

## Anahtar eşleme ve sonuç kuralları

1. Testcase içindeki tek `property name="test_case_id"` değeri kullanılır.
2. Bu özellik yoksa `testcase name` mevcut test vakası kimliğiyle **tam** eşleştirilir.
3. Anahtar önce ilgili projeye, mevcut gereksinim–test vakası bağlantıları üzerinden
   ait olmalıdır. Yalnızca global kimliğin var olması eşleşme için yeterli değildir.
4. Bilinmeyen kimlik: `unknown_test_case`; mevcut ama projeye bağlı olmayan kimlik:
   `not_linked_to_project`. Sonuç kaybolmaz; `test_case_id: null` olarak saklanır ve
   `unmatched_results` içinde geri döner. Yeni test vakası otomatik oluşturulmaz.
5. Özellik açıkça verilmiş ama eşleşmemişse isim üzerinden ikinci bir eşleme yapılmaz.
   Böylece hatalı bir anahtar gizlenmez. Sınıf adı veya test fonksiyonundan tahmini
   kimlik türetilmez. Parametreli testler için açık `test_case_id` önerilir.
6. `<failure>` veya `<error>` → `Failed`; `<skipped>` → `Skipped`; bunlar yoksa
   `Passed`. JUnit'in `error` öğesi ayrı bir `Blocked` sonucu olarak yorumlanmaz.
   Hem failure/error hem skipped içeren çelişkili kayıtlar reddedilir.
7. Tekrarlanan anahtarlar (ör. parametreli testler) ayrı sonuçlar olarak korunur.
   Aynı rapor tekrar gönderilirse yeni bir içe aktarım oluşur; idempotency yapılmaz.

`testsuite` ve `testsuites` kökleri, iç içe suite'ler ve XML namespace'leri desteklenir.
Desteklenmeyen sarmalayıcı öğeler altındaki suite/testcase kayıtları tüm raporun
`422` ile reddedilmesine neden olur; sonuçlar sessizce atlanmaz.
Dosyanın `tests`, `failures` gibi özet nitelikleri güvenilir kabul edilmez; sayılar gerçek
`testcase` kayıtlarından hesaplanır. Negatif/NaN/sonsuz süre reddedilir; süre yoksa null'dır.
DTD ve entity bildirimleri yasaktır; dış kaynak veya yerel dosya okunmaz.

## Kalıcılık, sınırlar ve yeniden görüntüleme

Yeni Alembic migrasyonu `0005`, yalnızca `imported_test_runs` ve
`imported_test_results` tablolarını ekler. Önceki migrasyonlar değiştirilmez.
`alembic upgrade head` ile kurulur; `alembic downgrade 0004` bu iki tabloyu ve
onların içe aktarım kayıtlarını kaldırır. Diğer proje/test/defect verisini değiştirmez. İçe aktarım geçmişi bulunan bir projenin
silinmesi `409` ile engellenir; geçmiş kayıtları sessizce kaybolmaz.

- Gövde en fazla **1 MiB**; rapor en fazla **5000** sonuç içerebilir.
- İsim, sınıf, suite ve bildirilen anahtar en fazla 512 karakter olabilir.
- Hatalı XML veya sonuç doğrulama hatasında `422`; boyut sınırında `413`; desteklenmeyen
  içerik türünde `415`; oturum yoksa `401`, rol uygun değilse `403`; proje yoksa `404`.
- Bağlı kayıtlar yazım sırasında çakışırsa `409`; kayıtlar tek transaction'da yazılır,
  kısmi sonuç bırakılmaz.
- Giriş yapmış kullanıcılar `GET /api/projects/{project_id}/runs/imports` ile özetleri,
  `GET /api/projects/{project_id}/runs/imports/{import_id}` ile kayıtlı eşleşme raporunu
  tekrar okuyabilir. Başka projenin import kimliği o proje altında okunamaz (`404`).
- Listeleme `limit` (1–100, varsayılan 50) ve `offset` (en az 0) parametrelerini destekler.
- Frontend istemci sözleşmesi `api.importJUnit`, `api.junitImports`, `api.junitImport`
  yardımcıları ve TypeScript tipleriyle hazırdır; bu işte yeni bir yönetim ekranı yoktur.

## Diğer plan maddeleriyle sınır

`main` üzerinde henüz PLN-17'nin Test Run/Test Execution modelleri yoktur. Bu nedenle
PLN-22 yalnızca **içe aktarım anlık görüntülerini** saklar; genel koşum CRUD API'si,
manüel yürütme ekranı, defect ↔ yürütme bağlantısı veya kapanış doğrulama şartı eklemez.
PLN-17 ile bütünleştirme için bu kayıtların ortak koşum/yürütme modeline taşınması
veya bağlanması ekipçe kararlaştırılmalıdır. `TestCase.status`, mevcut metrikler ve
immutable defect geçmişi içe aktarım tarafından değiştirilmez.

Cobertura içe aktarımı ve CI'ın sonuçları bu API'ye otomatik göndermesi PLN-23;
genişletilmiş metrikler PLN-24 kapsamındadır ve bu değişiklikte uygulanmaz.

## Doğrulama

```bash
cd backend
ruff check .
mypy app
python -m pytest -q --cov=app --cov-report=xml:coverage.xml
```

Yeni `test_junit_parser.py` ve `test_junit_import.py` testleri güvenli ayrıştırmayı,
sonuç eşlemesini, rol ve proje sınırlarını, üst veriyi, tekrar okumayı ve atomic
rollback'i denetler. Tüm migrasyonlar ayrıca atılabilir PostgreSQL veritabanında
çalıştırılmalıdır; testler şemayı sıfırladığı için gerçek veritabanı kullanılmaz.
