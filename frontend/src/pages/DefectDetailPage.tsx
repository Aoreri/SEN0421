import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  Defect,
  DefectHistoryEntry,
  formatErrorMessage,
  TestCase,
  User,
} from "../api";
import { ErrorAlert } from "../components/ErrorAlert";
import { StatusBadge } from "../components/StatusBadge";

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("tr-TR", {
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
  const { id } = useParams<{ id: string }>();
  const defectId = Number(id);
  const isValidId = Boolean(id) && Number.isInteger(defectId) && defectId > 0;

  const [defect, setDefect] = useState<Defect | null>(null);
  const [history, setHistory] = useState<DefectHistoryEntry[]>([]);
  const [linkedTestCase, setLinkedTestCase] = useState<TestCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const [error, setError] = useState("");

  const loadDetail = useCallback(async () => {
    if (!isValidId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const [allDefects, hist, allTestCases] = await Promise.all([
        api.defects(),
        api.defectHistory(defectId),
        api.testCases(),
      ]);
      const found = allDefects.find((d) => d.id === defectId) ?? null;
      setDefect(found);
      setHistory(hist);
      if (found?.test_case) {
        setLinkedTestCase(allTestCases.find((t) => t.id === found.test_case) ?? null);
      } else {
        setLinkedTestCase(null);
      }
      setError("");
    } catch (err) {
      setError(
        formatErrorMessage(err, "Defect detayları ve değişiklik geçmişi yüklenemedi."),
      );
    } finally {
      setLoading(false);
    }
  }, [defectId, isValidId]);

  useEffect(() => {
    setDefect(null);
    setHistory([]);
    setLinkedTestCase(null);
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
      setError(formatErrorMessage(err, "Durum geçişi sırasında bir hata oluştu."));
    } finally {
      setTransitioning(false);
    }
  }

  if (!isValidId) {
    return (
      <section>
        <p className="back-row">
          <Link to="/" className="back-link">
            ← Defect Listesine Dön
          </Link>
        </p>
        <h2>Geçersiz Defect Numarası</h2>
        <p>İstenen defect kimliği geçerli bir sayı değil.</p>
      </section>
    );
  }

  return (
    <>
      <ErrorAlert message={error} onDismiss={() => setError("")} />

      <section>
        <div className="detail-top-bar">
          <Link to="/" className="back-link">
            ← Defect Listesine Dön
          </Link>
          <span className="hint">IEEE 829 Test Incident Report · ISO/IEC/IEEE 29119-2</span>
        </div>

        {loading && !defect ? (
          <p className="hint">Yükleniyor...</p>
        ) : !defect ? (
          <div>
            <h2>Defect #{defectId} Bulunamadı</h2>
            <p className="section-desc">
              Bu numaraya ait bir defect kaydı mevcut değil.
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
                <span className="detail-label">Kayıt No</span>
                <strong>#{defect.id}</strong>
              </div>
              <div className="detail-item">
                <span className="detail-label">Önem Derecesi (Severity)</span>
                <div>
                  <StatusBadge text={defect.severity} />
                </div>
              </div>
              <div className="detail-item">
                <span className="detail-label">Mevcut Durum (Status)</span>
                <div>
                  <StatusBadge text={defect.status} />
                </div>
              </div>
              <div className="detail-item">
                <span className="detail-label">Bağlı Test Vakası (Test Case Specification)</span>
                <div>
                  {defect.test_case ? (
                    linkedTestCase ? (
                      <div className="linked-tc">
                        <strong>{linkedTestCase.id}</strong> · {linkedTestCase.title}{" "}
                        <StatusBadge text={linkedTestCase.status} />
                        <span className="hint">
                          (Gereksinim:{" "}
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
                    <span className="hint">Bağlı test vakası yok</span>
                  )}
                </div>
              </div>
            </div>

            <div className="transition-box">
              <h3>İzin Verilen Durum Geçişleri</h3>
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
                  Durum geçişi yapmak için{" "}
                  <Link to="/login">giriş yapın</Link>.
                </p>
              ) : (
                <p className="hint">
                  Aktif rolünüz (<StatusBadge text={user.role} />) için{" "}
                  <strong>{defect.status}</strong> durumundan yapılabilecek bir geçiş bulunmuyor.
                </p>
              )}
            </div>
          </>
        )}
      </section>

      {defect && (
        <section>
          <h2>Değişiklik Geçmişi Zaman Çizelgesi</h2>
          <p className="section-desc">
            Bu defect için kaydedilen tüm durum geçişleri kronolojik sırayla listelenir. Geçmiş
            tablosu değiştirilemez (append-only) yapıdadır.
          </p>

          {history.length === 0 ? (
            <p className="table-empty">Henüz geçmiş kaydı bulunamadı.</p>
          ) : (
            <ol className="timeline" role="list" aria-label="Defect Değişiklik Geçmişi">
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
                            <span className="timeline-event-tag">Oluşturuldu</span>
                            <span>→</span>
                            <StatusBadge text={entry.to} />
                          </>
                        ) : (
                          <>
                            <span className="timeline-event-tag">
                              {isReopen ? "Yeniden Açıldı (Reopen)" : "Durum Geçişi"}
                            </span>
                            <StatusBadge text={entry.from ?? "—"} />
                            <span>→</span>
                            <StatusBadge text={entry.to} />
                          </>
                        )}
                      </div>
                      <time className="timeline-time" dateTime={entry.at}>
                        {formatTimestamp(entry.at)}
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
