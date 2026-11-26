/**
 * Language state and translation lookup. Turkish is the default and the
 * Turkish text itself is the lookup key, so a missing English entry always
 * falls back to Turkish.
 *
 * No React imports here so the provider (`i18n.tsx`) and plain modules
 * (`api.ts`, `validation.ts`) share one implementation, and the unit test can
 * exercise `translate` without a DOM.
 */
export type Lang = "tr" | "en";

const STORAGE_KEY = "lang";

export function readStoredLang(): Lang {
  try {
    return localStorage.getItem(STORAGE_KEY) === "en" ? "en" : "tr";
  } catch {
    return "tr";
  }
}

export function storeLang(lang: Lang): void {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    // Storage can be unavailable (private mode, quota); the session keeps the choice.
  }
}

let current: Lang = readStoredLang();

/** Called by the provider so non-component modules follow the selected UI language. */
export function setCurrentLang(lang: Lang): void {
  current = lang;
}

export function translate(
  tr: string,
  vars?: Record<string, string | number>,
  lang: Lang = current,
): string {
  const template = (lang === "en" ? en[tr] : undefined) ?? tr;
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in vars ? String(vars[name]) : match,
  );
}

export const en: Record<string, string> = {
  "\"{name}\" gereksinimi silinsin mi? Bu işlem geri alınamaz.":
    "Delete the requirement \"{name}\"? This action cannot be undone.",
  "\"{name}\" projesi silinsin mi? Bu işlem geri alınamaz.":
    "Delete the project \"{name}\"? This action cannot be undone.",
  "\"{name}\" sürümü silinsin mi? Bu işlem geri alınamaz.":
    "Delete the release \"{name}\"? This action cannot be undone.",
  "\"{name}\" test koşumu başlatıldı.": "Test run \"{name}\" started.",
  "\"{name}\" önizleme koşumu olarak bu tarayıcıda oluşturuldu.":
    "\"{name}\" was created as a preview run in this browser.",
  "\"{title}\" ({version}) Test Plan kaydı silindi.":
    "Test Plan \"{title}\" ({version}) was deleted.",
  "\"{title}\" ({version}) Test Plan kaydı silinsin mi? Bu işlem geri alınamaz.":
    "Delete Test Plan \"{title}\" ({version})? This action cannot be undone.",
  "\"{title}\" ({version}) Test Plan taslağı oluşturuldu.":
    "Test Plan draft \"{title}\" ({version}) was created.",
  "\"{title}\" ({version}) taslağı güncellendi.":
    "Draft \"{title}\" ({version}) was updated.",
  "(Onaylı planı yeniden düzenlemek için": "(To re-edit an approved plan, use the",
  ") için": ") has no transition available from",
  "):": "):",
  "/ hedef ≥ {target}%": "/ target ≥ {target}%",
  "/ limit ≤ {limit}": "/ limit ≤ {limit}",
  "1. Kapsam (Scope)": "1. Scope",
  "1. Kapsam (Test Items & Features to be Tested)":
    "1. Scope (Test Items & Features to be Tested)",
  "1. İlgili ekranı açın\n2. Geçerli veriyi gönderin\n3. Yanıtı doğrulayın":
    "1. Open the relevant screen\n2. Submit valid data\n3. Verify the response",
  "2. Test Yaklaşımı (Approach)": "2. Test Approach",
  "3. Kabul / Red Kriterleri (Pass/Fail Criteria)": "3. Pass/Fail Criteria",
  "3. Kabul / Red ve Giriş / Çıkış Kriterleri (Pass/Fail Criteria)":
    "3. Pass/Fail and Entry/Exit Criteria (Pass/Fail Criteria)",
  "4. Test Ortamı ve Çıktılar (Environment & Deliverables)":
    "4. Test Environment & Deliverables",
  "4. Test Ortamı ve Çıktılar (Environment)": "4. Test Environment & Deliverables",
  "5. Takvim ve Riskler (Schedule & Risks)": "5. Schedule & Risks",
  "5. Takvim, Sorumluluklar ve Riskler (Schedule, Responsibilities & Risks)":
    "5. Schedule, Responsibilities & Risks",
  "Adım bilgisi tanımlanmamış.": "No step information defined.",
  "Adım tanımlanmamış.": "No step defined.",
  "Adımlar": "Steps",
  "Adımlar & Beklenen": "Steps & Expected",
  "Adımları Gizle": "Hide Steps",
  "Aktif Koşum:": "Active Test Run:",
  "Aktif Oturum:": "Active Session:",
  "Aktif Test Lead Muafiyeti:": "Active Test Lead Waiver:",
  "Aktif rol:": "Active role:",
  "Aktif rolünüz (": "Your active role (",
  "Alındığı Durum": "Status When Taken",
  "Ana Gezinme": "Main Navigation",
  "Anahtar": "Key",
  "Anahtar en fazla {max} karakter olabilir.":
    "Key can be at most {max} characters.",
  "Anahtar veya başlık ara...": "Search key or title...",
  "Anahtar yalnızca harf, rakam, '-' ve '_' içerebilir.":
    "Key may only contain letters, digits, '-' and '_'.",
  "Anlık Görüntü (Snapshot) Al": "Take Snapshot",
  "Anlık Görüntü (Snapshot) Kaydet": "Save Snapshot",
  "Anlık Görüntü Oluştur": "Create Snapshot",
  "Açık / İşlemde": "Open / In Progress",
  "Açık Critical Defect": "Open Critical Defects",
  "Açık Critical limiti 0 veya daha büyük tam sayı olmalıdır.":
    "The open Critical limit must be an integer of 0 or greater.",
  "Açık Defect": "Open Defects",
  "Açık Kalan: {count}": "Still Open: {count}",
  "Açık:": "Open:",
  "Açıklama": "Description",
  "Açıklama en fazla {max} karakter olabilir.":
    "Description can be at most {max} characters.",
  "Açılan": "Opened",
  "Backend'e ulaşılamadı. Önce backend'i başlatın (README'ye bakın).":
    "Could not reach the backend. Start the backend first (see README).",
  "Bağlanacak test vakalarını seçin:": "Select the test cases to link:",
  "Bağlantıları Kaydet": "Save Links",
  "Bağlı": "Linked",
  "Bağlı Gereksinimler": "Linked Requirements",
  "Bağlı Test Vakaları": "Linked Test Cases",
  "Bağlı Test Vakası (Test Case Specification)":
    "Linked Test Case (Test Case Specification)",
  "Bağlı değil": "Not linked",
  "Bağlı test vakası yok": "No linked test case",
  "Bağlı test yok": "No linked tests",
  "Başarı": "Pass Rate",
  "Başarı %": "Pass rate %",
  "Başarı Oranı": "Pass Rate",
  "Başarı oranı 0 ile 100 arasında olmalıdır.":
    "Pass rate must be between 0 and 100.",
  "Başarı:": "Pass rate:",
  "Başarısız Yürütmeden Defect Aç": "Open Defect from Failed Execution",
  "Başarısız Yürütmeden Yeni Defect Aç ({caseId})":
    "Open New Defect from Failed Execution ({caseId})",
  "Başarısız yürütmeden #{id} ({title}) defect kaydı oluşturuldu ve bağlandı.":
    "Defect #{id} ({title}) was created from the failed execution and linked.",
  "Başlatan": "Started By",
  "Başlatan:": "Started by:",
  "Başlık": "Title",
  "Başlık boş olamaz.": "Title cannot be empty.",
  "Başlık en az {min} karakter olmalıdır.": "Title must be at least {min} characters.",
  "Başlık en fazla {max} karakter olabilir.":
    "Title can be at most {max} characters.",
  "Beklenen Sonuç": "Expected Result",
  "Beklenen Sonuç (Expected Result)": "Expected Result",
  "Beklenen sonuç alanı boş olamaz.": "Expected result cannot be empty.",
  "Beklenen sonuç en fazla {max} karakter olabilir.":
    "Expected result can be at most {max} characters.",
  "Belirtilmedi.": "Not specified.",
  "Bilgileri Doldur": "Fill In",
  "Birim, entegrasyon, kabul testleri ve doğrulama stratejisi...":
    "Unit, integration and acceptance testing, and the verification strategy...",
  "Bu defect için kaydedilen tüm durum geçişleri kronolojik sırayla listelenir. Geçmiş tablosu değiştirilemez (append-only) yapıdadır.":
    "Every status transition recorded for this defect is listed in chronological order. The history table is append-only and cannot be modified.",
  "Bu numaraya ait bir defect kaydı mevcut değil.": "No defect exists with this number.",
  "Bu projede içe aktarım raporu bulunamadı.": "No import report found in this project.",
  "Bu test suite kapsamında koşulacak vakaları seçin.":
    "Select the test cases to execute in this suite.",
  "Canlı HTML": "Live HTML",
  "Canlı HTML Görüntüle": "View Live HTML",
  "Canlı PDF İndir": "Download Live PDF",
  "Canlı Rapor (HTML)": "Live Report (HTML)",
  "Canlı Rapor (PDF)": "Live Report (PDF)",
  "Canlı rapor veya saklanmış anlık görüntü (snapshot)": "Live report or stored snapshot",
  "Canlı veya saklanmış anlık görüntüden (snapshot) HTML ve PDF rapor üretimi":
    "HTML and PDF report generation from the live record or a stored snapshot",
  "Defect": "Defect",
  "Defect #{id} Bulunamadı": "Defect #{id} Not Found",
  "Defect Başlığı": "Defect Title",
  "Defect Burn-up (Açılan vs Kapatılan)": "Defect Burn-up (Opened vs Closed)",
  "Defect Değişiklik Geçmişi": "Defect Change History",
  "Defect Oluştur & Bağla": "Create & Link Defect",
  "Defect burn-up için henüz zaman serisi verisi yok.":
    "No time-series data for defect burn-up yet.",
  "Defect detayları ve değişiklik geçmişi yüklenemedi.":
    "Could not load defect details and change history.",
  "Defect oluşturmak ve durum geçişi yapmak için":
    "To create a defect or change its status,",
  "Defect oluşturulamadı.": "Could not create the defect.",
  "Defect oluşturulurken bir hata oluştu.":
    "An error occurred while creating the defect.",
  "Defect'ler": "Defects",
  "Demo Hesapları": "Demo Accounts",
  "Demo Kullanıcıları": "Demo Users",
  "Detay & Geçmiş": "Detail & History",
  "Detay & Zaman Çizelgesi": "Detail & Timeline",
  "Detaylı açıklama (isteğe bağlı)": "Detailed description (optional)",
  "Değişiklik Geçmişi Zaman Çizelgesi": "Change History Timeline",
  "Değişiklik şimdilik yalnızca bu tarayıcıda (önizleme) kaydedildi.":
    "The change was saved in this browser only (preview) for now.",
  "Doğrudan": "A direct",
  "Doğrulama Notu: İlişkili": "Verification note: the linked",
  "Durum": "Status",
  "Durum Geçişi": "Status Transition",
  "Durum Geçişi (API)": "Status Transition (API)",
  "Durum geçişi sırasında bir hata oluştu.":
    "An error occurred during the status transition.",
  "Durum geçişi yapmak için": "To change the status,",
  "Durum:": "Status:",
  "Düzenle": "Edit",
  "Düzenlemeyi İptal Et": "Cancel Editing",
  "Ekle": "Add",
  "Ekleniyor...": "Adding...",
  "Elle test vakası seç": "Select test cases manually",
  "En az bir test adımı girin (satır başına bir adım).":
    "Enter at least one test step (one step per line).",
  "Engelli": "Blocked",
  "Eşik Altında": "Below Threshold",
  "Eşikleri Gizle": "Hide Thresholds",
  "Eşikleri Kaydet": "Save Thresholds",
  "Eşleşen Vaka": "Matched Case",
  "Eşleşen:": "Matched:",
  "Eşleşmedi": "Not Matched",
  "Eşleşmeyen:": "Unmatched:",
  "FR-REQ-01 gereği en az bir gereksinim seçilmelidir.":
    "FR-REQ-01 requires selecting at least one requirement.",
  "FR-REQ-01 gereği her test vakası en az bir gereksinime bağlanmalıdır.":
    "FR-REQ-01 requires every test case to be linked to at least one requirement.",
  "FR-REQ-01 gereği {key} en az bir gereksinime bağlı kalmalıdır.":
    "FR-REQ-01 requires {key} to remain linked to at least one requirement.",
  "Genel": "General",
  "Genel (Sürüme bağlı değil)": "General (not tied to a release)",
  "Genişletilmiş metrikler ve sürüm çıkış kapısı değerleri canlı defect, gereksinim ve test vakası verileriyle önizleme test koşumlarından hesaplanır.":
    "Expanded metrics and release gate values are computed from live defect, requirement and test case data plus preview test runs.",
  "Gereksinim": "Requirement",
  "Gereksinim Ekle": "Add Requirement",
  "Gereksinim Kapsamı": "Requirement Coverage",
  "Gereksinim Kodu": "Requirement Code",
  "Gereksinim Test İzlenebilirlik Matrisi": "Requirement Test Traceability Matrix",
  "Gereksinim başlığı": "Requirement title",
  "Gereksinim başlığı boş olamaz.": "Requirement title cannot be empty.",
  "Gereksinim kapsamı 0 ile 100 arasında olmalıdır.":
    "Requirement coverage must be between 0 and 100.",
  "Gereksinim kaydedilirken bir hata oluştu.":
    "An error occurred while saving the requirement.",
  "Gereksinim kodu boş olamaz (örn. R9).": "Requirement code cannot be empty (e.g. R9).",
  "Gereksinim kodu en fazla {max} karakter olabilir.":
    "Requirement code can be at most {max} characters.",
  "Gereksinim silinirken bir hata oluştu.":
    "An error occurred while deleting the requirement.",
  "Gereksinim – Test İzlenebilirlik Matrisi": "Requirement – Test Traceability Matrix",
  "Gereksinim ↔ Test Vakası izlenebilirlik bağlantılarını güncelleyebilirsiniz. Proje/sürüm/gereksinim ekleme ve silme işlemleri Admin veya Test Lead rolü gerektirir.":
    "You can update Requirement ↔ Test Case traceability links. Adding and deleting projects, releases and requirements requires the Admin or Test Lead role.",
  "Gereksinim:": "Requirement:",
  "Gereksinimi Güncelle": "Update Requirement",
  "Gereksinimler": "Requirements",
  "Gereksinimler ve Test Vakası İzlenebilirliği":
    "Requirements and Test Case Traceability",
  "Gereksinimler ve mevcut test vakaları canlı okunur; mevcut test vakalarının matris değişiklikleri kalıcı olarak kaydedilir. Yeni test vakaları, adım/öncelik/otomasyon alanları ve test suite işlemleri şimdilik yalnızca bu tarayıcıda saklanır.":
    "Requirements and existing test cases are read live; matrix changes to existing test cases are persisted. New test cases, step/priority/automation fields and test suite operations are stored in this browser only for now.",
  "Gerçekleşen Sonuç": "Actual Result",
  "Geçerli bir proje seçin.": "Select a valid project.",
  "Geçerli bir test vakası seçin.": "Select a valid test case.",
  "Geçerli bir öncelik seçin.": "Select a valid priority.",
  "Geçerli bir önem derecesi seçin.": "Select a valid severity.",
  "Geçersiz Defect Numarası": "Invalid Defect Number",
  "Geçersiz defect bilgisi.": "Invalid defect information.",
  "Geçiş": "Transition",
  "Geçmiş": "History",
  "Geçti": "Passed",
  "Giriş Ekranına Git": "Go to Login",
  "Giriş Yap": "Sign In",
  "Giriş yapılırken bir hata oluştu.": "An error occurred while signing in.",
  "Giriş yapılıyor...": "Signing in...",
  "Gizle": "Hide",
  "Grafik için henüz test koşumu verisi yok.": "No test run data for the chart yet.",
  "Grafikli Metrik Paneli": "Metrics Dashboard",
  "Gözlemlenen davranış / çıktı": "Observed behaviour / output",
  "Güncelle": "Update",
  "HTML / PDF İndir": "Download HTML / PDF",
  "HTML Görüntüle": "View HTML",
  "Hata mesajını kapat": "Dismiss error message",
  "Hedef Sürüm": "Target Release",
  "Hedef Sürüm (Opsiyonel)": "Target Release (Optional)",
  "Hedef Sürüm:": "Target Release:",
  "Henüz geçmiş kaydı bulunamadı.": "No history entries yet.",
  "Henüz sürüm yok.": "No releases yet.",
  "Her satır bir gereksinimi, her sütun bir test vakasını temsil eder.":
    "Each row represents a requirement and each column a test case.",
  "Her snapshot alındığı andaki Test Plan metnini, gereksinim izlenebilirliğini, test vakalarını, defect kayıtlarını ve metrik özetini değiştirilemez olarak saklar ve o sürüme ait HTML / PDF indirilmesini sağlar.":
    "Each snapshot stores the Test Plan text, requirement traceability, test cases, defect records and metric summary immutably at the moment it is taken, and allows the HTML / PDF for that version to be downloaded.",
  "Hücrelere tıklayarak bağlantıyı doğrudan güncelleyebilirsiniz.":
    "Click cells to update links directly.",
  "Hızlı Seçim": "Quick Select",
  "IEEE 829 Test Incident Report Çıktısı & Anlık Görüntüler":
    "IEEE 829 Test Incident Report Output & Snapshots",
  "IEEE 829 Test Plan kayıtlarını görüntülüyorsunuz ve HTML/PDF olarak indirebilirsiniz. Taslak oluşturmak, düzenlemek veya durum geçişi yapmak için giriş yapın.":
    "You are viewing IEEE 829 Test Plan records and can download them as HTML/PDF. Sign in to create drafts, edit them or change status.",
  "IEEE 829 Test Plan · Yeni planlar": "IEEE 829 Test Plan · New plans start in",
  "IEEE 829 Test Planları & HTML/PDF →": "IEEE 829 Test Plans & HTML/PDF →",
  "JUnit Raporları": "JUnit Reports",
  "JUnit İçe Aktarım Raporları": "JUnit Import Reports",
  "Kabul/Red kriterleri en fazla {max} karakter olabilir.":
    "Pass/fail criteria can be at most {max} characters.",
  "Kapat": "Close",
  "Kapatılan": "Closed",
  "Kapatılan:": "Closed:",
  "Kapsam Eksikliği (Gap):": "Coverage Gap:",
  "Kapsam alanı en fazla {max} karakter olabilir.":
    "Scope can be at most {max} characters.",
  "Kapsam ve hedef koşum notu": "Scope and target run note",
  "Kapsamsız": "Uncovered",
  "Kapsanan Gereksinim": "Covered Requirements",
  "Kararlı Anahtar": "Stable Key",
  "Kararlı test anahtarı boş olamaz (örn. TC-007).":
    "Stable test key cannot be empty (e.g. TC-007).",
  "Karşılandı": "Met",
  "Katalog kayıtlarını salt okunur görüntülüyorsunuz.":
    "You are viewing catalog records in read-only mode.",
  "Kaydediliyor...": "Saving...",
  "Kayıt No": "Record No",
  "Kayıtlı Test Lead Muafiyeti (Kriterler sağlandığı için pasif):":
    "Recorded Test Lead Waiver (inactive because the criteria are met):",
  "Kayıtlı Test Planları": "Saved Test Plans",
  "Kod": "Code",
  "Koşum Adı": "Test Run Name",
  "Koşum Başına Sonuç Dağılımı & Başarı Trendi":
    "Result Distribution per Test Run & Pass Rate Trend",
  "Koşum Oranı": "Execution Rate",
  "Koşum adı boş olamaz.": "Test run name cannot be empty.",
  "Koşum adı en az {min} karakter olmalıdır.":
    "Test run name must be at least {min} characters.",
  "Koşum adı en fazla {max} karakter olabilir.":
    "Test run name can be at most {max} characters.",
  "Koşum adı veya #ID ara...": "Search test run name or #ID...",
  "Koşum başına yığılmış test sonuçları ve başarı oranı trend grafiği":
    "Stacked test results per run and pass rate trend chart",
  "Koşum geçmişinde ara": "Search test run history",
  "Koşum ilerleme çubuğu: {executed}/{total} yürütüldü":
    "Test run progress bar: {executed}/{total} executed",
  "Koşuma Alınacak Test Vakaları": "Test Cases to Include in the Run",
  "Koşuma en az bir test vakası eklenmelidir.":
    "At least one test case must be added to the run.",
  "Kullanıcı Adı": "Username",
  "Kullanıcı Girişi": "User Login",
  "Kullanıcı adı boş olamaz.": "Username cannot be empty.",
  "Limit Aşıldı": "Limit Exceeded",
  "Maks. Açık Critical Defect": "Max. Open Critical Defects",
  "Manuel": "Manual",
  "Matris oluşturmak için en az bir gereksinim ve bir test vakası bulunmalıdır.":
    "At least one requirement and one test case are needed to build the matrix.",
  "Metrik Paneli": "Metrics Dashboard",
  "Mevcut Durum (Status)": "Current Status",
  "Min. Başarı Oranı (%)": "Min. Pass Rate (%)",
  "Min. Gereksinim Kapsamı (%)": "Min. Requirement Coverage (%)",
  "Muafiyet Kaydet": "Save Waiver",
  "Muafiyet gerekçesi boş olamaz.": "Waiver reason cannot be empty.",
  "Muafiyet gerekçesi en az 5 karakter olmalıdır.":
    "Waiver reason must be at least 5 characters.",
  "Muafiyet gerekçesi en fazla {max} karakter olabilir.":
    "Waiver reason can be at most {max} characters.",
  "Muafiyet kaldırılamadı.": "Could not remove the waiver.",
  "Muafiyet kaydedilemedi.": "Could not save the waiver.",
  "Muafiyeti Kaldır": "Remove Waiver",
  "Not": "Note",
  "Oluşturan:": "Created by:",
  "Oluşturuldu": "Created",
  "Onaylanmış (Approved) Test Plan düzenlenemez; önce Draft durumuna alın":
    "An Approved Test Plan cannot be edited; move it to Draft first",
  "Onaylanmış (Approved) Test Plan silinemez": "An Approved Test Plan cannot be deleted",
  "Onaylayan:": "Approved by:",
  "Ort. Defect Yaşı": "Avg. Defect Age",
  "Ort. Çözüm Süresi": "Avg. Resolution Time",
  "Ortam veya kısa not": "Environment or short note",
  "Otomasyon": "Automation",
  "Otomasyona göre filtrele": "Filter by automation",
  "Otomatik": "Automated",
  "Otomatik + Manuel": "Automated + Manual",
  "Otomatik Defect": "Automatic Defect",
  "Otomatikleştirilmiş test vakası (CI/CD ile koşulur)":
    "Automated test case (run via CI/CD)",
  "Oturum doğrulanıyor...": "Verifying session...",
  "PDF İndir": "Download PDF",
  "Panel & Metrikler": "Dashboard & Metrics",
  "Parola": "Password",
  "Parola boş olamaz.": "Password cannot be empty.",
  "Parola en fazla 72 bayt olabilir.": "Password can be at most 72 bytes.",
  "Parolanızı girin": "Enter your password",
  "Plan Sürüm Numarası": "Plan Version Number",
  "Plan Sürümü": "Plan Version",
  "Plan Sürümü:": "Plan Version:",
  "PostgreSQL 16, FastAPI, React/Vite, GitHub Actions CI ortamı...":
    "PostgreSQL 16, FastAPI, React/Vite, GitHub Actions CI environment...",
  "Proje": "Project",
  "Proje #{id}": "Project #{id}",
  "Proje / Sürüm": "Project / Release",
  "Proje Adı": "Project Name",
  "Proje Adı (#{id})": "Project Name (#{id})",
  "Proje Ekle": "Add Project",
  "Proje Filtresi:": "Project Filter:",
  "Proje adı boş olamaz.": "Project name cannot be empty.",
  "Proje adı en fazla {max} karakter olabilir.":
    "Project name can be at most {max} characters.",
  "Proje açıklaması (isteğe bağlı)": "Project description (optional)",
  "Proje kaydedilirken bir hata oluştu.":
    "An error occurred while saving the project.",
  "Proje seçin": "Select a project",
  "Proje silinirken bir hata oluştu.": "An error occurred while deleting the project.",
  "Proje ve gereksinim verileri yüklenemedi. Önce backend'i başlatın.":
    "Could not load project and requirement data. Start the backend first.",
  "Proje, sürüm ve gereksinim kayıtlarını görüntülüyorsunuz. Düzenleme veya izlenebilirlik eşleştirmesi yapmak için giriş yapın.":
    "You are viewing project, release and requirement records. Sign in to edit or to map traceability.",
  "Proje:": "Project:",
  "Projeler": "Projects",
  "Projeler & Gereksinimler": "Projects & Requirements",
  "Projeler yüklenemedi": "Could not load projects",
  "Projeyi Güncelle": "Update Project",
  "Rapor yüklenemedi": "Could not load the report",
  "Rapor yükleniyor...": "Loading report...",
  "Raporlar yüklenemedi": "Could not load reports",
  "Raporları görmek için": "To see the reports,",
  "Rol": "Role",
  "Rol tabanlı işlemleri (defect oluşturma, durum geçişleri, proje/sürüm/gereksinim yönetimi ve izlenebilirlik) gerçekleştirmek için giriş yapın.":
    "Sign in to perform role-based operations (defect creation, status transitions, project/release/requirement management and traceability).",
  "Salt okunur": "Read-only",
  "Salt okunur görünüm.": "Read-only view.",
  "Seçilen projenin son 50 içe aktarımı. Başarısız sonuçtan açılan veya yeniden kullanılan defect bağlantısı raporda korunur.":
    "The last 50 imports of the selected project. Defects opened from or reused by a failed result keep their link in the report.",
  "Seçili": "Selected",
  "Sil": "Delete",
  "Snapshot #{id} Özeti": "Snapshot #{id} Summary",
  "Snapshot Alınıyor...": "Taking Snapshot...",
  "Snapshot içeriği yüklenemedi.": "Could not load snapshot content.",
  "Son Durum": "Latest Status",
  "Son yürüten:": "Last executed by:",
  "Sonucu Kaydet": "Save Result",
  "Sonuç": "Result",
  "Sonuç Dağılımı": "Result Distribution",
  "Sprint takvimi, roller ve RSK kayıtlarına referanslar...":
    "Sprint schedule, roles and references to RSK risk records...",
  "Sprintler yüklenemedi.": "Could not load sprints.",
  "Suite": "Suite",
  "Suite Adı": "Test Suite Name",
  "Suite Güncelle": "Update Suite",
  "Suite Oluştur": "Create Suite",
  "Suite adı boş olamaz.": "Suite name cannot be empty.",
  "Suite adı en az 2 karakter olmalıdır.": "Suite name must be at least 2 characters.",
  "Suite adı en fazla {max} karakter olabilir.":
    "Suite name can be at most {max} characters.",
  "Suite atanmadı": "No test suite assigned",
  "Suite İçindeki Test Vakaları": "Test Cases in the Test Suite",
  "Suite Şablonu (Opsiyonel)": "Test Suite Template (Optional)",
  "Suite şimdilik yalnızca bu tarayıcıda (önizleme) kaydedildi.":
    "The suite was saved in this browser only (preview) for now.",
  "Suite'e göre filtrele": "Filter by test suite",
  "Sürüm": "Release",
  "Sürüm (#{id})": "Release (#{id})",
  "Sürüm Durumu": "Release Status",
  "Sürüm Durumu:": "Release Status:",
  "Sürüm Ekle": "Add Release",
  "Sürüm Geçmişi": "Version History",
  "Sürüm Geçmişi ve Anlık Görüntüler (Snapshots)": "Version History and Snapshots",
  "Sürüm Yönetimi": "Release Management",
  "Sürüm Yönetimi & Test Summary Report →":
    "Release Management & Test Summary Report →",
  "Sürüm bilgisi boş olamaz.": "Release information cannot be empty.",
  "Sürüm durumu \"{status}\" olarak güncellendi.":
    "Release status updated to \"{status}\".",
  "Sürüm durumu \"{status}\" olarak yerel önizleme deposuna kaydedildi.":
    "Release status updated to \"{status}\" in the local preview store.",
  "Sürüm durumu güncelleme ve eşik yapılandırma yalnızca":
    "Updating release status and configuring thresholds is reserved for the",
  "Sürüm durumu güncellenemedi.": "Could not update the release status.",
  "Sürüm en fazla {max} karakter olabilir.":
    "Release can be at most {max} characters.",
  "Sürüm kaydedilirken bir hata oluştu.":
    "An error occurred while saving the release.",
  "Sürüm numarası boş olamaz (örn. v1.0).": "Version number cannot be empty (e.g. v1.0).",
  "Sürüm numarası en fazla {max} karakter olabilir.":
    "Version number can be at most {max} characters.",
  "Sürüm seçilmedi": "No release selected",
  "Sürüm silinirken bir hata oluştu.": "An error occurred while deleting the release.",
  "Sürüm verileri yüklenemedi.": "Could not load release data.",
  "Sürüm Çıkış Kapısı": "Release Exit Gate",
  "Sürüm Çıkış Kapısı:": "Release Exit Gate:",
  "Sürüm çıkış kriterleri güncellendi.": "Release exit criteria updated.",
  "Sürüm çıkış kriterleri yerel önizleme deposunda güncellendi.":
    "Release exit criteria updated in the local preview store.",
  "Sürüm:": "Release:",
  "Sürüme göre filtrele": "Filter by release",
  "Sürümler (Releases)": "Releases",
  "Sürümler yüklenemedi.": "Could not load releases.",
  "Sürümü Güncelle": "Update Release",
  "Takvim ve riskler alanı en fazla {max} karakter olabilir.":
    "Schedule and risks can be at most {max} characters.",
  "Tam HTML Raporu Aç": "Open Full HTML Report",
  "Tanı Mesajı": "Diagnostic Message",
  "Tanımlanmamış.": "Not defined.",
  "Tarih": "Date",
  "Taslağı Düzenle": "Edit Draft",
  "Taslağı Formda Düzenle": "Edit Draft in Form",
  "Test Adımları": "Test Steps",
  "Test Adımları (Test Procedure)": "Test Steps (Test Procedure)",
  "Test Adımları (her satıra bir adım)": "Test Steps (one step per line)",
  "Test Bağla": "Link Test",
  "Test Başarı Oranı": "Test Pass Rate",
  "Test Incident Report anlık görüntüsü oluşturulamadı.":
    "Could not create the Test Incident Report snapshot.",
  "Test Incident Report indirilemedi.": "Could not download the Test Incident Report.",
  "Test Koşum Geçmişi": "Test Run History",
  "Test Koşumları": "Test Runs",
  "Test Koşumu Başlat": "Start Test Run",
  "Test Koşumu Başlat / Yürüt →": "Start / Execute Test Run →",
  "Test Lead Muafiyeti Gerekçesi (Kriterler karşılanmasa da sürüm çıkışını onaylamak için)":
    "Test Lead Waiver Reason (to approve the release exit even when the criteria are not met)",
  "Test Lead muafiyeti kaldırıldı.": "Test Lead waiver removed.",
  "Test Lead muafiyeti kaydedildi.": "Test Lead waiver saved.",
  "Test Lead muafiyeti yerel önizleme deposuna kaydedildi.":
    "Test Lead waiver saved in the local preview store.",
  "Test Lead muafiyeti yerel önizleme deposundan kaldırıldı.":
    "Test Lead waiver removed from the local preview store.",
  "Test Log indirilemedi.": "Could not download the Test Log.",
  "Test Plan #{id} ({version}) durumu \"{from}\" → \"{to}\" olarak güncellendi.":
    "Test Plan #{id} ({version}) status changed from \"{from}\" to \"{to}\".",
  "Test Plan #{id} ({version}) için Snapshot #{snapshot} ({status}) kaydedildi.":
    "Snapshot #{snapshot} ({status}) saved for Test Plan #{id} ({version}).",
  "Test Plan Başlığı": "Test Plan Title",
  "Test Plan Detayı & Sürüm Geçmişi:": "Test Plan Detail & Version History:",
  "Test Plan Taslağı Oluştur": "Create Test Plan Draft",
  "Test Plan Taslağını Düzenle (#{id})": "Edit Test Plan Draft (#{id})",
  "Test Plan Taslağını Güncelle": "Update Test Plan Draft",
  "Test Plan anlık görüntüsü (snapshot) alabilir ve HTML/PDF indirebilirsiniz. Taslak oluşturma, düzenleme ve Draft → In Review → Approved durum geçişleri Admin veya Test Lead rolü gerektirir.":
    "You can take Test Plan snapshots and download HTML/PDF. Creating and editing drafts and the Draft → In Review → Approved status transitions require the Admin or Test Lead role.",
  "Test Plan anlık görüntüsü (snapshot) alınamadı.":
    "Could not take a Test Plan snapshot.",
  "Test Plan başlığı boş olamaz.": "Test Plan title cannot be empty.",
  "Test Plan detayı ve sürüm geçmişi yüklenemedi.":
    "Could not load the Test Plan detail and version history.",
  "Test Plan durum geçişi yapılamadı.":
    "Could not perform the Test Plan status transition.",
  "Test Plan indirilemedi.": "Could not download the Test Plan.",
  "Test Plan kaydedilirken bir hata oluştu.":
    "An error occurred while saving the Test Plan.",
  "Test Plan kayıtlarını salt okunur görüntülüyorsunuz ve HTML/PDF indirebilirsiniz.":
    "You are viewing Test Plan records read-only and can download HTML/PDF.",
  "Test Plan silinirken bir hata oluştu.":
    "An error occurred while deleting the Test Plan.",
  "Test Plan verileri yüklenemedi. Önce backend'i başlatın.":
    "Could not load Test Plan data. Start the backend first.",
  "Test Planları": "Test Plans",
  "Test Suite": "Test Suite",
  "Test Suite Düzenle": "Edit Test Suite",
  "Test Suite'ler": "Test Suites",
  "Test Summary Report anlık görüntüsü #{id} oluşturuldu.":
    "Test Summary Report snapshot #{id} created.",
  "Test Summary Report anlık görüntüsü oluşturulamadı.":
    "Could not create the Test Summary Report snapshot.",
  "Test Summary Report indirilemedi.": "Could not download the Test Summary Report.",
  "Test Tamamlama · Sürüm durumu, çıkış kriterleri, muafiyet ve IEEE 829 Test Summary Report":
    "Test Completion · Release status, exit criteria, waiver and IEEE 829 Test Summary Report",
  "Test Tasarımı Görünümleri": "Test Design Views",
  "Test Tasarımı ve Gerçekleştirme": "Test Design and Implementation",
  "Test Tasarımı ve Gerçekleştirme · Gereksinim ↔ Test Vakası çoka-çok izlenebilirlik matrisi":
    "Test Design and Implementation · Requirement ↔ Test Case many-to-many traceability matrix",
  "Test Vakaları": "Test Cases",
  "Test Vakaları & Matris": "Test Cases & Matrix",
  "Test Vakası": "Test Case",
  "Test Vakası / Suite & Matris Yönetimi →":
    "Test Case / Suite & Matrix Management →",
  "Test Vakası Adım Detayları": "Test Case Step Details",
  "Test Vakası Başlığı": "Test Case Title",
  "Test Vakası Ekle": "Add Test Case",
  "Test Vakası Kataloğu": "Test Case Catalog",
  "Test Vakası, Suite ve İzlenebilirlik Yönetimi":
    "Test Case, Suite and Traceability Management",
  "Test Vakasını Düzenle ({key})": "Edit Test Case ({key})",
  "Test Yürütme ve Test Olay Raporlama":
    "Test Execution and Test Incident Reporting",
  "Test edilecek modüller, özellikler ve kapsam dışı bırakılanlar...":
    "Modules to be tested, features and items out of scope...",
  "Test koşumları yüklenemedi.": "Could not load test runs.",
  "Test koşumu başlatmak, sonuç girmek veya başarısız yürütmeden defect açmak için":
    "To start a test run, record a result or open a defect from a failed execution,",
  "Test koşumu oluşturulamadı.": "Could not create the test run.",
  "Test koşumu ve yürütme kayıtları şimdilik yalnızca bu tarayıcıda saklanır. Başarısız yürütmeden açtığınız defect kayıtları ise kalıcı olarak kaydedilir.":
    "Test run and execution records are stored in this browser only for now. Defects you open from a failed execution are persisted.",
  "Test koşumu yürütme işlemleri yalnızca": "Test run execution is reserved for",
  "Test ortamı alanı en fazla {max} karakter olabilir.":
    "Test environment can be at most {max} characters.",
  "Test suite kaydedildi.": "Test suite saved.",
  "Test suite kaydedilemedi.": "Could not save the test suite.",
  "Test suite silinemedi.": "Could not delete the test suite.",
  "Test vakaları ve izlenebilirlik verileri yüklenemedi.":
    "Could not load test cases and traceability data.",
  "Test vakası": "Test case",
  "Test vakası ara": "Search test cases",
  "Test vakası başlığı boş olamaz.": "Test case title cannot be empty.",
  "Test vakası kaydedildi.": "Test case saved.",
  "Test vakası kaydedilemedi.": "Could not save the test case.",
  "Test vakası silinemedi.": "Could not delete the test case.",
  "Test vakası, suite ve izlenebilirlik matrisi düzenleme işlemleri için":
    "To edit test cases, suites and the traceability matrix,",
  "Test vakası/suite yönetimi ve matris düzenleme yalnızca":
    "Test case/suite management and matrix editing are reserved for",
  "Test İzleme ve Kontrol · Koşum trendi, defect burn-up ve önem dağılımı":
    "Test Monitoring and Control · Run trend, defect burn-up and severity distribution",
  "Test İzleme ve Kontrol · Seçili sürüm":
    "Test Monitoring and Control · Selected release",
  "Test İzleme ve Kontrol · Sürüm Yayınlama Kriterleri":
    "Test Monitoring and Control · Release Publication Criteria",
  "Toplam Açılan:": "Total Opened:",
  "Toplam Gereksinim": "Total Requirements",
  "Toplam Kapatılan:": "Total Closed:",
  "Toplam Test": "Total Tests",
  "Toplam İzlenebilirlik Bağı": "Total Traceability Links",
  "Toplam:": "Total:",
  "Tüm Projeler": "All Projects",
  "Tüm Suite'ler": "All Test Suites",
  "Tüm Sürümler": "All Releases",
  "Tüm sprintler": "All sprints",
  "Tüm Öncelikler": "All Priorities",
  "Tümünü Seç": "Select All",
  "Vaka atanmadı": "No cases assigned",
  "Vazgeç": "Cancel",
  "Yaklaşım alanı en fazla {max} karakter olabilir.":
    "Approach can be at most {max} characters.",
  "Yalnızca API'nin izin verdiği durum geçişleri gösterilir.":
    "Only status transitions allowed by the API are shown.",
  "Yalnızca Manuel": "Manual Only",
  "Yalnızca Otomatik": "Automated Only",
  "Yaşam döngüsü:": "Life cycle:",
  "Yeni IEEE 829 Test Plan Taslağı Oluştur":
    "Create New IEEE 829 Test Plan Draft",
  "Yeni Test Koşumu Başlat": "Start New Test Run",
  "Yeni Test Suite": "New Test Suite",
  "Yeni Test Vakası": "New Test Case",
  "Yeni defect başlığı (en az 3 karakter)":
    "New defect title (at least 3 characters)",
  "Yeni defect kaydı yalnızca Admin, Test Lead veya Tester rolleri tarafından oluşturulabilir.":
    "Only the Admin, Test Lead or Tester roles can create new defects.",
  "Yeniden Açıldı (Reopen)": "Reopened (Reopen)",
  "Yeniden Açılma Oranı": "Reopen Rate",
  "Yetki Özeti": "Permission Summary",
  "Yükleniyor...": "Loading...",
  "Yürüt / İncele": "Execute / Inspect",
  "Yürütme sonucu kaydedilemedi.": "Could not save the execution result.",
  "Zaman içinde açılan ve kapatılan defect burn-up grafiği":
    "Defect burn-up chart of opened and closed defects over time",
  "başarı oranı": "pass rate",
  "defect kayıtları": "defect records are in",
  "durumda. Burada": "status. Recording a",
  "durumuna alınmadan düzenlenemez veya silinemez.": "status.",
  "durumuna geçirilmelidir.": "status first.",
  "durumunda başlar;": "status;",
  "durumundaki planlar tekrar":
    "plans can only be edited or deleted after moving them back to",
  "durumundan yapılabilecek bir geçiş bulunmuyor.": ".",
  "ekranından bir sürüm tanımlayın.": "screen: define a release there.",
  "geçişi kullanılır).": "transition).",
  "geçişi yapılamaz; önce": "transition is not allowed; move it to",
  "giriş yapın": "sign in",
  "kapsamında": "scope",
  "rolleri içindir.": "roles.",
  "sa": "h",
  "ve": "and",
  "ve sprint": "and sprint",
  "yürütmesi başarısız": "execution failed",
  "yürütmesi kaydetmek doğrulama kanıtı oluşturur.":
    "execution here provides verification evidence.",
  "{caseId} yürütme sonucu ({status}) kaydedildi.":
    "{caseId} execution result ({status}) saved.",
  "{caseId} yürütme sonucu ({status}) yerel önizleme deposuna kaydedildi.":
    "{caseId} execution result ({status}) saved in the local preview store.",
  "{code} · {title} — Test Vakası Bağlantıları":
    "{code} · {title} — Test Case Links",
  "{count} açık": "{count} open",
  "{count} açık, {closed} kapalı": "{count} open, {closed} closed",
  "{count} snapshot": "{count} snapshot",
  "{count} sonuç": "{count} results",
  "{count} test": "{count} tests",
  "{count} vaka": "{count} cases",
  "{key} silindi.": "{key} deleted.",
  "{key} yerel önizleme deposundan kaldırıldı.":
    "{key} removed from the local preview store.",
  "{name} silindi.": "{name} deleted.",
  "{name} yerel önizleme deposundan silindi.":
    "{name} deleted from the local preview store.",
  "{requirements} gereksinimlerine henüz test vakası bağlanmamış.":
    "No test cases are linked to these requirements yet: {requirements}.",
  "{req} ve {caseKey} bağlantısı: {state}": "{req} and {caseKey} link: {state}",
  "Çıktı & İndirme": "Output & Download",
  "Çıkış Eşikleri Düzenle": "Edit Exit Thresholds",
  "Çıkış Kapısı": "Exit Gate",
  "Çıkış Kapısı Engelli": "Exit Gate Blocked",
  "Çıkış Kapısı Geçti": "Exit Gate Passed",
  "Çıkış Yap": "Sign Out",
  "Çıkış kapısı değerlendirmesi için önce bir sürüm tanımlayın.":
    "Define a release first to evaluate the exit gate.",
  "Çıkış kriterleri güncellenemedi.": "Could not update the exit criteria.",
  "Çıkış kriterleri karşılanmadan veya muafiyet girilmeden Ready/Released yapılamaz":
    "Cannot move to Ready/Released until the exit criteria are met or a waiver is recorded",
  "Önceki ve aktif test koşumlarını sürüm veya ada göre filtreleyip inceleyin.":
    "Filter and inspect previous and active test runs by release or name.",
  "Öncelik": "Priority",
  "Önceliğe göre filtrele": "Filter by priority",
  "Önem": "Severity",
  "Önem Derecesi": "Severity",
  "Önem Derecesi (Severity)": "Severity",
  "Önem Derecesine Göre Defect Dağılımı": "Defect Distribution by Severity",
  "Önizleme Modu:": "Preview Mode:",
  "Önizlemeyi Kapat": "Close Preview",
  "Örn: Başarı oranı >= %80, açık Critical defect = 0, gereksinim kapsamı >= %80...":
    "E.g. pass rate >= 80%, open Critical defects = 0, requirement coverage >= 80%...",
  "Örn: Bilinen düşük etkili sorun sonraki yamaya ertelendi.":
    "E.g. A known low-impact issue was deferred to the next patch.",
  "Örn: HTTP 201 döner ve kayıt listede görünür.":
    "E.g. HTTP 201 is returned and the record appears in the list.",
  "Örn: R9": "E.g. R9",
  "Örn: SDS-06": "E.g. SDS-06",
  "Örn: SDS-06 Sürüm 1.0 Master Test Planı":
    "E.g. SDS-06 Release 1.0 Master Test Plan",
  "Örn: Sprint 2 Regresyon Paketi": "E.g. Sprint 2 Regression Pack",
  "Örn: Sürüm çıkış kapısı doğrulaması": "E.g. Release exit gate verification",
  "Örn: TC-007": "E.g. TC-007",
  "Örn: tester": "E.g. tester",
  "Örn: v0.1.0": "E.g. v0.1.0",
  "Örn: v1.0 veya 0.2-draft": "E.g. v1.0 or 0.2-draft",
  "Örn: v1.0 Çıkış Öncesi Regresyon": "E.g. v1.0 Pre-release Regression",
  "Özet (P / F / B / NR)": "Summary (P / F / B / NR)",
  "Üreten": "Generated By",
  "Üreten:": "Generated by:",
  "Üretim Zamanı": "Generated At",
  "İndir": "Download",
  "İptal": "Cancel",
  "İstanbul Kültür Üniversitesi · Software Development with Standards · v1.0":
    "Istanbul Kültür University · Software Development with Standards · v1.0",
  "İstenen defect kimliği geçerli bir sayı değil.":
    "The requested defect ID is not a valid number.",
  "İzin Verilen Durum Geçişleri": "Allowed Status Transitions",
  "İzin Verilen Durum Geçişleri (Draft → In Review → Approved)":
    "Allowed Status Transitions (Draft → In Review → Approved)",
  "İzlenebilirlik Matrisi": "Traceability Matrix",
  "İzlenebilirlik bağlantıları güncellenemedi.":
    "Could not update traceability links.",
  "İzlenebilirlik bağlantısı güncellenemedi.":
    "Could not update the traceability link.",
  "İçe Aktarım": "Import",
  "İçerik Özeti": "Content Summary",
  "İşlem": "Action",
  "İşlemler": "Actions",
  "← Defect Listesine Dön": "← Back to Defect List",

  // Default table state and ARIA labels supplied by DataTable callers.
  "Kayıt bulunamadı.": "No records found.",
  "Kayıtlı test vakası bulunamadı.": "No saved test cases found.",
  "Defect Listesi": "Defect List",
  "Kayıtlı defect bulunamadı.": "No saved defects found.",
  "Kayıtlı test koşumu bulunamadı.": "No saved test runs found.",
  "JUnit İçe Aktarım Sonuçları": "JUnit Import Results",
  "Kayıtlı Test Plan bulunamadı.": "No saved Test Plans found.",
  "Bu Test Plan için henüz kaydedilmiş bir sürüm anlık görüntüsü (snapshot) bulunmuyor.":
    "No saved version snapshot exists for this Test Plan yet.",
  "Test Plan Sürüm Geçmişi": "Test Plan Version History",
  "Filtrelerle eşleşen test vakası bulunamadı.":
    "No test cases matched the filters.",
  "Test Vakaları Kataloğu": "Test Case Catalog",
  "Henüz tanımlı test suite yok.": "No test suite defined yet.",
  "Test Suite Listesi": "Test Suite List",
  "Bu sürüm için henüz Test Summary Report anlık görüntüsü yok.":
    "No Test Summary Report snapshot exists for this release yet.",
  "Test Summary Report anlık görüntüleri": "Test Summary Report snapshots",
  "Kayıtlı proje bulunamadı.": "No saved projects found.",
  "Kayıtlı sürüm bulunamadı.": "No saved releases found.",
  "Sürümler": "Releases",
  "Kayıtlı gereksinim bulunamadı.": "No saved requirements found.",

  // Client-side API fallbacks (backend `detail` strings are shown as returned).
  "Geçersiz istek gönderildi.": "The request was invalid.",
  "Oturum süresi doldu veya kimlik doğrulama gerekli.":
    "The session expired or authentication is required.",
  "Bu işlem için yetkiniz yok.": "You are not authorized for this operation.",
  "İstenen kayıt bulunamadı.": "The requested record was not found.",
  "Kayıt başka verilerle veya durum kurallarıyla çakışıyor.":
    "The record conflicts with other data or with the status rules.",
  "Gönderilen form verileri doğrulamadan geçemedi.":
    "The submitted form data failed validation.",
  "Sunucu hatası oluştu. Lütfen daha sonra tekrar deneyin.":
    "A server error occurred. Please try again later.",
  "Backend servisine ulaşılamadı. Önce backend'i başlatın (README'ye bakın).":
    "Could not reach the backend service. Start the backend first (see README).",
  "Servis şu anda kullanılamıyor.": "The service is currently unavailable.",
  "İstek işlenirken bir hata oluştu.": "An error occurred while processing the request.",
  "İşlem sırasında beklenmeyen bir hata oluştu.":
    "An unexpected error occurred during the operation.",

  // Demo account summaries on the login screen.
  "Tüm katalog, izlenebilirlik ve defect geçiş yetkileri":
    "Full catalog, traceability and defect transition permissions",
  "Proje/sürüm/gereksinim yönetimi, defect doğrulama ve kapatma":
    "Project/release/requirement management, defect verification and closure",
  "Defect oluşturma, izlenebilirlik eşleştirme, Resolved → Closed / Reopen":
    "Defect creation, traceability mapping, Resolved → Closed / Reopen",
  "Open → In Progress → Resolved defect durum geçişleri":
    "Open → In Progress → Resolved defect status transitions",
};
