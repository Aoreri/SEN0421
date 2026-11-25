# PLN-35 — Performans ve birim test kapsamı ölçüm raporu

**Sorumlu:** Esra Kaya · **Hedef tarih / ölçüm günü:** 24.11.2026  
**Standart:** ISO/IEC/IEEE 12207 — Doğrulama ve Ölçme; ISO/IEC 25010 —
performans verimliliği (zaman davranışı) ve bakım yapılabilirlik (test edilebilirlik).

## Sonuç

Kaydedilen PostgreSQL referans ortamında üç PLN-35 eşiği de sağlandı:
10.000 yürütmeli panel <2 saniye, mevcut Test Plan üretim işlemleri <10 saniye,
iş akışı/metrik modüllerinin her birinde birim test kapsamı ≥%80.
Karar bütün örneklerin **en yüksek süresine** göre verildi; ilk örnek,
aykırı değerler veya başarısız denemeler silinmedi. Bunlar kaydedilen ortamın
ölçümleridir; bütün donanımlar için süre garantisi değildir.

- Ölçülen uygulama kodu: PR #45 head [`97bdc7e`](https://github.com/Aoreri/SEN0421/commit/97bdc7eafb8c52ce90f227e371ad7e6623679470), GitHub'ın `main` ile birleştirme commit'i `5456f3e` üzerinde. Sonraki commit yalnızca kanıt, belge, test ve kapsam betiğini değiştirir; ölçülen uygulama kodu (`backend/app`, `frontend/src`, `quality/`) aynıdır.
- Ölçüm başlangıcı (UTC): `2026-11-25T15:43:25.896Z`.
- [PostgreSQL/tarayıcı ölçüm işi](https://github.com/Aoreri/SEN0421/actions/runs/45648086892) — başarılı.
- [Backend, PostgreSQL, frontend ve birim kapsam kontrolleri](https://github.com/Aoreri/SEN0421/pull/45/checks) — başarılı.
- Kalıcı sayısal kanıt: [tüm süre örnekleri ve ortam bilgileri](evidence/pln35-performance.json), [birim kapsam özeti](evidence/pln35-unit-coverage.json).
- Ayrıntılı JSON/Cobertura ve performans tanıları, Actions altında `workflow-metrics-unit-coverage` ve `pln35-performance` çıktılarında 14 gün saklanır.

## Ortam ve veri kümesi

| Bileşen | Gerçek ölçüm ortamı |
| --- | --- |
| Çalıştırıcı | GitHub Actions `ubuntu-latest`, Linux `7.0.0-1016-aws` |
| CPU | Intel(R) Xeon(R) 6975P-C; 4 mantıksal işlemci |
| RAM | 16463400960 bayt (~15.33 GiB) |
| Python / Node | 3.12.16 / v22.23.5 |
| PostgreSQL / Chromium | 16.16 / 159.0.8154.6 |
| Sunum | Üretim Vite build'i + Vite preview, gerçek FastAPI/Uvicorn; 1280×800, DPR 1 |
| Eşzamanlılık | Tek kullanıcı; localhost HTTP. Docker imajı veya geniş alan ağı yük testi değildir. |

Boş, yalnızca bu işe ait `sds06_pln35_benchmark` veritabanına gerçek Alembic
migrasyonları uygulandı. **100 koşum × 100 vaka = tam 10.000 etkileşimli
TestExecution** kaydı oluşturuldu: 7.000 Passed, 1.000 Failed, 1.000 Blocked,
1.000 Skipped. API'nin 10.000 toplam ve %87,5 başarı oranı döndürdüğü doğrulandı.
Bunlar JUnit import anlık görüntüleri veya önizleme verileri değildir.

Migrasyon tohumları korundu: toplam 106 test vakası,
103 defect, 8 gereksinim ve
253 değiştirilemez geçmiş kaydı vardı. Bu sayılara eklenen
100 defect ve 100 vaka dahildir. Vaka–gereksinim ve yürütme–defect bağlantıları
gerçektir. Bütün yürütmeler seçili sürüme aittir; ikinci, boş kontrol sürümüyle
panelin 10.000 → 0 → 10.000 geçişi ayrıca doğrulandı.

## Süre sonuçları

Bütün değerler **milisaniye**; sınırlar katıdır (`<`, eşitlik yeterli değildir).
P95 en yakın üst sıra yöntemiyle hesaplandı. Çift örnek sayısında
medyan sütunu üst ortanca (`median_high`) değerini kullanır. Küçük örnek kümesinde p95'in
maksimuma eşit olması normaldir.

| İşlem | Örnek | İlk | Üst medyan | P95 | Maksimum | Sınır | Karar |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Panel açılışı (tarayıcı) | 10 | 326.597 | 208.383 | 326.597 | **326.597** | < 2,000 | Geçti |
| Test Plan HTML üretimi | 5 | 68.514 | 25.820 | 68.514 | **68.514** | < 10,000 | Geçti |
| Test Plan PDF üretimi | 5 | 1905.189 | 987.887 | 1905.189 | **1905.189** | < 10,000 | Geçti |
| Test Plan snapshot üretimi | 5 | 30.869 | 30.178 | 34.888 | **34.888** | < 10,000 | Geçti |

Panel için her açılışta yeni Chromium bağlamı kullanıldı; tarayıcı cache’i örnekler arasında paylaşılmaz ve API
yanıtı taklidi yoktur. Kimlik doğrulama işlemi sayaç dışındadır; kayıtlı
oturumun geri yüklenmesi, sayfa gezintisi, sekiz gerçek panel veri isteği,
10.000 değerinin ve grafiğin DOM'da görünmesi, iki animation frame sayaç
**içindedir**. İlk örnek uygulamanın ilk panel sorgularını da kapsar.
Sonraki örnekler yeni tarayıcı bağlamı kullanır; backend sorgu/şablon cache'i
ısınmış olabilir. İlk doküman üretim çağrısı da örneklerden çıkarılmadı.

Doküman süreleri HTTP gövdesinin tamamının okunmasını kapsar. HTML'de plan
başlığı, PDF'de Content-Type / `%PDF-` / `%%EOF`, snapshot'ta plan kimliği
kontrol edildi. PDF ölçümü mevcut WeasyPrint/yedek PDF yolunun uç nokta
süresidir; bu çalışma tipografi veya görsel eşdeğerlik onayı değildir.

### Ölçümle bulunan ve giderilen gecikme

İlk yerel tanıda oturum geri yüklenmesi ve varsayılan sürüm seçimi aynı panel
verilerinin tekrarlı yüklenmesine yol açıyordu. Oturum hazır olana kadar panel
başlatılmıyor; varsayılan seçim yeni bir yüklemeyi tetiklemiyor. Bağımsız
metrik/çıkış-kapısı istekleri paralel başlatılıyor. Geç gelen eski bir sürüm
isteği yeni seçimi ezemiyor. Referans çalışmadaki 10 açılışın tamamında her
panel veri isteğinin **tam bir kez** yapıldığı doğrulandı. Kullanıcının sürüm
seçimi ve tersine dönüşü gerçek API cevaplarıyla kontrol edildi.

Yerel SQLite tanılarında, sınırlı ve eşzamanlı test yükü olan hostta soğuk
panel açılışı 2 saniyeyi aşabildi. Bu sonuçlar başarılı sayılıp referans yerine
konmadı. Kabul kararı yukarıdaki ayrı PostgreSQL çalıştırıcısındaki gerçek
10 örneğe aittir; rapor farklı ortamların sayılarından tek bir sonuç üretmez.

## Ayrı birim test kapsamı

`pytest -m unit` ile **96 veritabanından bağımsız birim testi** çalıştı.
Entegrasyon testleri bu kapsama dahil edilmedi. Hedef modüllerin hiçbirinde
kapsam dışı bırakılmış satır yoktur. Her dosyada satır ve dal kapsamı ayrı ayrı
≥%80 olmak zorundadır; dosyalar arası ortalama bir açığı gizleyemez.

| Modül | Satır | Dal | ≥%80 kararı |
| --- | ---: | ---: | --- |
| `app/main.py` | 93/93 (%100) | 26/26 (%100) | Geçti |
| `app/runs.py` | 108/108 (%100) | 24/24 (%100) | Geçti |
| `app/metrics.py` | 102/102 (%100) | 40/40 (%100) | Geçti |

Session çiftleriyle rol/durum geçişi, doğrulama şartı, ilk geçmiş kaydı,
eksik kayıt, bağlantı/deduplication, boş payda, tarih aralığı ve UTC dönüşü
sınırları test edildi. Bu birim ölçümü, sahte Session sonuçlarının gerçek SQL
sorgularını doğruladığı anlamına gelmez. Gerçek SQL popülasyonları, kalıcılık
ve PostgreSQL geçmiş trigger'ı ayrı entegrasyon paketinde doğrulanır.
Tam CI: SQLite **232 geçti / 2 PostgreSQL testi atlandı**; PostgreSQL
**234 geçti**; frontend lint, tip kontrolü ve üretim build'i başarılı.

## ISO/IEC 25010 tablosuna aktarılacak girdiler

| Kalite alt niteliği | Ölçü / hedef | Gerçek sonuç | Durum / sınır |
| --- | --- | --- | --- |
| Performans verimliliği — zaman davranışı | 10.000 yürütmeli panel <2 sn | En yüksek 0.477769 sn; 10/10 örnek geçti | Referans ortamında sağlandı |
| Performans verimliliği — zaman davranışı | Doküman üretimi <10 sn | HTML en yüksek 0.061091 sn; PDF 2.172398 sn; snapshot 0.037082 sn | Mevcut Test Plan uçları; her işlemde 5/5 geçti |
| Bakım yapılabilirlik — test edilebilirlik | İş akışı ve metrik modüllerinde ≥%80 birim kapsam | `main`, `runs`, `metrics`: her birinde %100 satır ve %100 dal | 96 bağımsız birim testi; bütün ürün kalitesinin tek başına kanıtı değildir |

## Kapsam, yeniden üretim ve entegrasyon

[Çalıştırma yönergesi](../quality/README.md) ve
[ölçüm kodu](../quality/measure.mjs) bütün parametreleri ve temizleme
sorumluluğunu belirtir. Veri hazırlayıcı dolu veya uygun ad taşımayan
veritabanını reddeder; hiçbir mevcut tabloyu silmez. Yalnızca atılabilir demo
verisi kullanılır; canlı veri, `.env` veya gerçek kimlik bilgisi okunmaz.

Bu kod tabanının `main` dalında mevcut olan **Test Plan** HTML/PDF/snapshot
üretimi ölçüldü. Henüz birleşmemiş PLN-30 Test Summary Report ve PLN-39
Test Incident Report/Test Log türleri için süre iddiası yoktur. Bu işler veya
PLN-29 güvenlik değişiklikleri birleştikten sonra aynı ölçüm yeniden
çalıştırılmalı; yeni rapor türleri için ayrı örnekler eklenmelidir. Bu PR başka
bir PR'ın dalına dayanmaz ve şema/migrasyon/API sözleşmesi değiştirmez.
