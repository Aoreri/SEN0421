import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  Defect,
  DefectHistoryEntry,
  formatErrorMessage,
  TestCase,
  TestIncidentReportSnapshotSummary,
  User,
} from "../api";
import { ErrorAlert } from "../components/ErrorAlert";
import { StatusBadge } from "../components/StatusBadge";
import { useLang, useT } from "../i18n";

function formatTimestamp(iso: string, lang: "tr" | "en"): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString(lang === "tr" ? "tr-TR" : "en-GB", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export type DefectDetailPageProps = {
  user: User | null;
};

export function DefectDetailPage({ user }: DefectDetailPageProps) {
  const t = useT();
  const lang = useLang();
  const { id } = useParams<{ id: string }>();
  const defectId = Number(id);
  const isValidId = Boolean(id) && Number.isInteger(defectId) && defectId > 0;

  const [defect, setDefect] = useState<Defect | null>(null);
  const [history, setHistory] = useState<DefectHistoryEntry[]>([]);
  const [linkedTestCase, setLinkedTestCase] = useState<TestCase | null>(null);
  const [snapshots, setSnapshots] = useState<TestIncidentReportSnapshotSummary[]>([]);
  const [creatingSnapshot, setCreatingSnapshot] = useState(false);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const [error, setError] = useState("");

  const loadDetail = useCallback(async () => {
    if (!isValidId || !user) {
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const [allDefects, hist, allTestCases, snaps] = await Promise.all([
        api.defects(),
        api.defectHistory(defectId),
        api.testCases(),
        api.incidentReportSnapshots(defectId).catch(() => []),
      ]);
      const found = allDefects.find((d) => d.id === defectId) ?? null;
      setDefect(found);
      setHistory(hist);
      setSnapshots(snaps);
      if (found?.test_case) {
        setLinkedTestCase(allTestCases.find((t) => t.id === found.test_case) ?? null);
      } else {
        setLinkedTestCase(null);
      }
      setError("");
    } catch (err) {
      setError(
        formatErrorMessage(err, t("Defect detayları ve değişiklik geçmişi yüklenemedi.")),
      );
    } finally {
      setLoading(false);
    }
  }, [defectId, isValidId, user, t]);

  useEffect(() => {
    setDefect(null);
    setHistory([]);
    setLinkedTestCase(null);
    setSnapshots([]);
    setError("");
  }, [defectId]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail, user]);

  async function handleTransition(to: string) {
    if (!defect) return;
    setTransitioning(true);
    try {
      await api.transition(defect.id, to);
      setError("");
      await loadDetail();
    } catch (err) {
      setError(formatErrorMessage(err, t("Durum geçişi sırasında bir hata oluştu.")));
    } finally {
      setTransitioning(false);
    }
  }

  const canCreateSnapshot =
    user !== null &&
    (user.role === "Admin" || user.role === "Test Lead" || user.role === "Tester");

  // Export routes require the bearer token, so a plain <a href> would get 401.
  async function handleDownload(defectId: number, format: "html" | "pdf", snapshotId?: number) {
    try {
      await api.downloadIncidentReport(defectId, format, snapshotId);
    } catch (err) {
      setError(formatErrorMessage(err, t("Test Incident Report indirilemedi.")));
    }
  }

  async function handleCreateSnapshot() {
    if (!defect || !canCreateSnapshot) return;
    setCreatingSnapshot(true);
    try {
      await api.createIncidentReportSnapshot(defect.id);
      setError("");
      await loadDetail();
    } catch (err) {
      setError(formatErrorMessage(err, t("Test Incident Report anlık görüntüsü oluşturulamadı.")));
    } finally {
      setCreatingSnapshot(false);
    }
  }

  if (!isValidId) {
    return (
      <section>
        <p className="back-row">
          <Link to="/" className="back-link">
            {t("← Defect Listesine Dön")}
          </Link>
        </p>
        <h2>{t("Geçersiz Defect Numarası")}</h2>
        <p>{t("İstenen defect kimliği geçerli bir sayı değil.")}</p>
      </section>
    );
  }

  return (
    <>
      <ErrorAlert message={error} onDismiss={() => setError("")} />

      <section>
        <div className="detail-top-bar">
          <Link to="/" className="back-link">
            {t("← Defect Listesine Dön")}
          </Link>
          <span className="hint">IEEE 829 Test Incident Report</span>
        </div>

        {loading && !defect ? (
          <p className="hint">{t("Yükleniyor...")}</p>
        ) : !defect ? (
          <div>
            <h2>{t("Defect #{id} Bulunamadı", { id: defectId })}</h2>
            <p className="section-desc">
              {t("Bu numaraya ait bir defect kaydı mevcut değil.")}
            </p>
          </div>
        ) : (
          <>
            <div className="detail-title-row">
              <h2>
                Defect #{defect.id} · {defect.title}
              </h2>
              <div className="badge-list">
                <StatusBadge text={defect.severity} />
                <StatusBadge text={defect.status} />
              </div>
            </div>

            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">{t("Kayıt No")}</span>
                <strong>#{defect.id}</strong>
              </div>
              <div className="detail-item">
                <span className="detail-label">{t("Önem Derecesi (Severity)")}</span>
                <div>
                  <StatusBadge text={defect.severity} />
                </div>
              </div>
              <div className="detail-item">
                <span className="detail-label">{t("Mevcut Durum (Status)")}</span>
                <div>
                  <StatusBadge text={defect.status} />
                </div>
              </div>
              <div className="detail-item">
                <span className="detail-label">
                  {t("Bağlı Test Vakası (Test Case Specification)")}
                </span>
                <div>
                  {defect.test_case ? (
                    linkedTestCase ? (
                      <div className="linked-tc">
                        <strong>{linkedTestCase.id}</strong> · {linkedTestCase.title}{" "}
                        <StatusBadge text={linkedTestCase.status} />
                        <span className="hint">
                          ({t("Gereksinim:")}{" "}
                          {linkedTestCase.requirements && linkedTestCase.requirements.length > 0
                            ? linkedTestCase.requirements.join(", ")
                            : linkedTestCase.requirement}
                          )
                        </span>
                      </div>
                    ) : (
                      <strong>{defect.test_case}</strong>
                    )
                  ) : (
                    <span className="hint">{t("Bağlı test vakası yok")}</span>
                  )}
                </div>
              </div>
            </div>

            <div className="transition-box">
              <h3>{t("İzin Verilen Durum Geçişleri")}</h3>
              {defect.allowed.length > 0 ? (
                <div className="row-actions">
                  {defect.allowed.map((to) => (
                    <button
                      key={to}
                      type="button"
                      disabled={transitioning}
                      onClick={() => void handleTransition(to)}
                    >
                      {defect.status} → {to}
                    </button>
                  ))}
                </div>
              ) : !user ? (
                <p className="hint">
                  {t("Durum geçişi yapmak için")}{" "}
                  <Link to="/login">{t("giriş yapın")}</Link>.
                </p>
              ) : (
                <p className="hint">
                  {t("Aktif rolünüz (")}
                  <StatusBadge text={user.role} />
                  {t(") için")} <strong>{defect.status}</strong>{" "}
                  {t("durumundan yapılabilecek bir geçiş bulunmuyor.")}
                </p>
              )}
            </div>
          </>
        )}
      </section>

      {defect && (
        <section>
          <div className="section-header">
            <div>
              <h2>{t("IEEE 829 Test Incident Report Çıktısı & Anlık Görüntüler")}</h2>
              <p className="section-desc">
                {t("Canlı veya saklanmış anlık görüntüden (snapshot) HTML ve PDF rapor üretimi")}
              </p>
            </div>
            <div className="row-actions">
              <button
                type="button"
                className="btn-link secondary-btn"
                onClick={() => void handleDownload(defect.id, "html")}
              >
                {t("Canlı HTML")}
              </button>
              <button
                type="button"
                className="btn-link secondary-btn"
                onClick={() => void handleDownload(defect.id, "pdf")}
              >
                {t("Canlı PDF İndir")}
              </button>
              {canCreateSnapshot && (
                <button
                  type="button"
                  disabled={creatingSnapshot}
                  onClick={() => void handleCreateSnapshot()}
                >
                  {creatingSnapshot ? t("Kaydediliyor...") : t("Anlık Görüntü (Snapshot) Al")}
                </button>
              )}
            </div>
          </div>

          {snapshots.length > 0 && (
            <div className="badge-list" style={{ marginTop: 8 }}>
              {snapshots.map((snap) => (
                <span key={snap.id} className="badge">
                  Snapshot #{snap.id} ({snap.status} · {snap.generated_by} ·{" "}
                  {formatTimestamp(snap.generated_at, lang)}){" "}
                  <button
                    type="button"
                    className="detail-link"
                    onClick={() => void handleDownload(defect.id, "html", snap.id)}
                  >
                    HTML
                  </button>{" "}
                  |{" "}
                  <button
                    type="button"
                    className="detail-link"
                    onClick={() => void handleDownload(defect.id, "pdf", snap.id)}
                  >
                    PDF
                  </button>
                </span>
              ))}
            </div>
          )}
        </section>
      )}

      {defect && (
        <section>
          <h2>{t("Değişiklik Geçmişi Zaman Çizelgesi")}</h2>
          <p className="section-desc">
            {t(
              "Bu defect için kaydedilen tüm durum geçişleri kronolojik sırayla listelenir. Geçmiş tablosu değiştirilemez (append-only) yapıdadır.",
            )}
          </p>

          {history.length === 0 ? (
            <p className="table-empty">{t("Henüz geçmiş kaydı bulunamadı.")}</p>
          ) : (
            <ol
              className="timeline"
              role="list"
              aria-label={t("Defect Değişiklik Geçmişi")}
            >
              {history.map((entry, index) => {
                const isInitial = entry.from === null;
                const isReopen = entry.from !== null && entry.to === "Open";
                return (
                  <li
                    key={`${entry.at}-${index}`}
                    className={`timeline-item${isInitial ? " timeline-initial" : ""}${
                      isReopen ? " timeline-reopen" : ""
                    }`}
                  >
                    <div className="timeline-marker" aria-hidden="true">
                      {index + 1}
                    </div>
                    <div className="timeline-content">
                      <div className="timeline-transition">
                        {isInitial ? (
                          <>
                            <span className="timeline-event-tag">{t("Oluşturuldu")}</span>
                            <span>→</span>
                            <StatusBadge text={entry.to} />
                          </>
                        ) : (
                          <>
                            <span className="timeline-event-tag">
                              {isReopen ? t("Yeniden Açıldı (Reopen)") : t("Durum Geçişi")}
                            </span>
                            <StatusBadge text={entry.from ?? "—"} />
                            <span>→</span>
                            <StatusBadge text={entry.to} />
                          </>
                        )}
                      </div>
                      <time className="timeline-time" dateTime={entry.at}>
                        {formatTimestamp(entry.at, lang)}
                      </time>
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </section>
      )}
    </>
  );
}
