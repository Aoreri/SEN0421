import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import {
  api,
  ApiError,
  AUTH_EXPIRED_EVENT,
  clearStoredToken,
  Defect,
  DefectHistoryEntry,
  ExitCriteriaConfig,
  ExpandedMetrics,
  formatErrorMessage,
  getStoredToken,
  isEndpointUnavailableError,
  Metrics,
  Release,
  ReleaseGateStatus,
  ReleaseStatus,
  SEVERITIES,
  TestCase,
  TestRun,
  User,
} from "./api";
import { DataTable, DataTableColumn } from "./components/DataTable";
import { ErrorAlert } from "./components/ErrorAlert";
import { FormField } from "./components/FormField";
import { MetricsCharts } from "./components/MetricsCharts";
import { ReleaseGateCard } from "./components/ReleaseGateCard";
import { StatusBadge } from "./components/StatusBadge";
import { DefectDetailPage } from "./pages/DefectDetailPage";
import { LoginPage } from "./pages/LoginPage";
import { JUnitImportsPage } from "./pages/JUnitImportsPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ReleasesPage } from "./pages/ReleasesPage";
import { TestCasesPage } from "./pages/TestCasesPage";
import { TestPlansPage } from "./pages/TestPlansPage";
import { TestRunsPage } from "./pages/TestRunsPage";
import {
  computePreviewExpandedMetrics,
  createPreviewReleaseWaiver,
  deletePreviewReleaseWaiver,
  loadPreviewReleaseGate,
  loadPreviewTestRuns,
  mergeTestCasesWithPreview,
  updatePreviewExitCriteria,
  updatePreviewReleaseStatus,
} from "./previewStore";
import { DefectFormErrors, hasFormErrors, validateDefectForm } from "./validation";

const TEST_CASE_COLUMNS: DataTableColumn<TestCase>[] = [
  { key: "id", header: "ID", render: (t) => t.id },
  { key: "title", header: "Başlık", render: (t) => t.title },
  {
    key: "requirement",
    header: "Gereksinim",
    render: (t) =>
      t.requirements && t.requirements.length > 0 ? t.requirements.join(", ") : t.requirement,
  },
  { key: "status", header: "Durum", render: (t) => <StatusBadge text={t.status} /> },
];

type DashboardViewProps = {
  user: User | null;
};

function DashboardView({ user }: DashboardViewProps) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [expandedMetrics, setExpandedMetrics] = useState<ExpandedMetrics | null>(null);
  const [tests, setTests] = useState<TestCase[]>([]);
  const [defects, setDefects] = useState<Defect[]>([]);
  const [releases, setReleases] = useState<Release[]>([]);
  const [selectedReleaseId, setSelectedReleaseId] = useState<number | null>(null);
  const [releaseGate, setReleaseGate] = useState<ReleaseGateStatus | null>(null);
  const [analyticsPreviewMode, setAnalyticsPreviewMode] = useState(false);
  const [gateSaving, setGateSaving] = useState(false);

  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState("Medium");
  const [testCase, setTestCase] = useState("");
  const [formErrors, setFormErrors] = useState<DefectFormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [transitioningId, setTransitioningId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const canCreateDefect =
    user !== null &&
    (user.role === "Admin" || user.role === "Test Lead" || user.role === "Tester");

  const load = useCallback(async () => {
    if (!user) {
      setMetrics(null);
      setExpandedMetrics(null);
      setTests([]);
      setDefects([]);
      setReleases([]);
      setReleaseGate(null);
      setError("");
      return;
    }
    try {
      const [m, t, d, projs, rels, reqs] = await Promise.all([
        api.metrics(),
        api.testCases(),
        api.defects(),
        api.projects(),
        api.releases(),
        api.requirements(),
      ]);

      const projectsWithRequirements = new Set(reqs.map((req) => req.project_id));
      const realReleases = rels.filter(
        (r) =>
          projectsWithRequirements.has(r.project_id) &&
          !r.version.startsWith("Mevcut projeler:"),
      );
      const selectableReleases = realReleases.length > 0 ? realReleases : rels;

      const activeReleaseId =
        selectedReleaseId && selectableReleases.some((r) => r.id === selectedReleaseId)
          ? selectedReleaseId
          : (selectableReleases[0]?.id ?? null);
      const activeRelease = selectableReleases.find((r) => r.id === activeReleaseId) ?? null;

      let isAnalyticsPreview = false;
      let loadedExpanded: ExpandedMetrics;
      try {
        loadedExpanded = await api.expandedMetrics(activeReleaseId);
      } catch (err) {
        if (isEndpointUnavailableError(err)) {
          isAnalyticsPreview = true;
          const mergedCases = mergeTestCasesWithPreview(t);
          let runs: TestRun[];
          try {
            runs = await api.testRuns();
          } catch (runErr) {
            if (isEndpointUnavailableError(runErr)) {
              runs = loadPreviewTestRuns(projs, selectableReleases, mergedCases, d);
            } else {
              throw runErr;
            }
          }
          const historyEntries = await Promise.all(
            d.map(async (def) => {
              try {
                return [def.id, await api.defectHistory(def.id)] as const;
              } catch {
                return [def.id, [] as DefectHistoryEntry[]] as const;
              }
            }),
          );
          const historiesByDefect = Object.fromEntries(historyEntries);
          loadedExpanded = computePreviewExpandedMetrics(
            m,
            mergedCases,
            reqs,
            d,
            historiesByDefect,
            runs,
            activeReleaseId,
            activeRelease?.project_id ?? null,
          );
        } else {
          throw err;
        }
      }

      let loadedGate: ReleaseGateStatus | null = null;
      if (activeRelease && !activeRelease.version.startsWith("Mevcut projeler:")) {
        try {
          loadedGate = await api.releaseGate(activeRelease.id);
        } catch (err) {
          if (isEndpointUnavailableError(err)) {
            isAnalyticsPreview = true;
            loadedGate = loadPreviewReleaseGate(activeRelease, loadedExpanded, d);
          } else {
            throw err;
          }
        }
      }

      setMetrics(loadedExpanded);
      setExpandedMetrics(loadedExpanded);
      setTests(t);
      setDefects(d);
      setReleases(selectableReleases);
      setSelectedReleaseId(activeReleaseId);
      setReleaseGate(loadedGate);
      setAnalyticsPreviewMode(isAnalyticsPreview);
      setError("");
    } catch (err) {
      setError(
        formatErrorMessage(
          err,
          "Backend'e ulaşılamadı. Önce backend'i başlatın (README'ye bakın).",
        ),
      );
    }
  }, [selectedReleaseId, user]);

  useEffect(() => {
    void load();
  }, [load, user]);

  async function addDefect(e: FormEvent) {
    e.preventDefault();
    const validationErrors = validateDefectForm(
      { title, severity, testCase },
      tests.map((t) => t.id),
    );
    setFormErrors(validationErrors);
    if (hasFormErrors(validationErrors)) {
      return;
    }

    setSubmitting(true);
    try {
      await api.createDefect(title, severity, testCase || null);
      setTitle("");
      setTestCase("");
      setFormErrors({});
      setError("");
      await load();
    } catch (err) {
      setError(formatErrorMessage(err, "Defect oluşturulurken bir hata oluştu."));
    } finally {
      setSubmitting(false);
    }
  }

  async function move(id: number, to: string) {
    setTransitioningId(id);
    try {
      await api.transition(id, to);
      setError("");
      await load();
    } catch (err) {
      setError(formatErrorMessage(err, "Durum geçişi sırasında bir hata oluştu."));
    } finally {
      setTransitioningId(null);
    }
  }

  async function handleUpdateReleaseStatus(status: ReleaseStatus) {
    const activeRelease = releases.find((r) => r.id === selectedReleaseId);
    if (!activeRelease || !expandedMetrics) return;
    setGateSaving(true);
    try {
      const updated = await api.updateReleaseStatus(activeRelease.id, status);
      setReleaseGate(updated);
      setNotice(`Sürüm durumu "${status}" olarak güncellendi.`);
      setError("");
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        const updated = updatePreviewReleaseStatus(
          activeRelease,
          status,
          expandedMetrics,
          defects,
        );
        setReleaseGate(updated);
        setAnalyticsPreviewMode(true);
        setNotice(`Sürüm durumu "${status}" olarak yerel önizleme deposuna kaydedildi.`);
        setError("");
      } else {
        setError(formatErrorMessage(err, "Sürüm durumu güncellenemedi."));
      }
    } finally {
      setGateSaving(false);
    }
  }

  async function handleUpdateExitCriteria(criteria: ExitCriteriaConfig): Promise<boolean> {
    const activeRelease = releases.find((r) => r.id === selectedReleaseId);
    if (!activeRelease || !expandedMetrics) return false;
    setGateSaving(true);
    try {
      const updated = await api.updateExitCriteria(activeRelease.id, criteria);
      setReleaseGate(updated);
      setNotice("Sürüm çıkış kriterleri güncellendi.");
      setError("");
      return true;
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        const updated = updatePreviewExitCriteria(
          activeRelease,
          criteria,
          expandedMetrics,
          defects,
        );
        setReleaseGate(updated);
        setAnalyticsPreviewMode(true);
        setNotice("Sürüm çıkış kriterleri yerel önizleme deposunda güncellendi.");
        setError("");
        return true;
      } else {
        setError(formatErrorMessage(err, "Çıkış kriterleri güncellenemedi."));
        return false;
      }
    } finally {
      setGateSaving(false);
    }
  }

  async function handleCreateWaiver(reason: string) {
    const activeRelease = releases.find((r) => r.id === selectedReleaseId);
    if (!activeRelease || !expandedMetrics || !user) return;
    setGateSaving(true);
    try {
      const updated = await api.createReleaseWaiver(activeRelease.id, reason);
      setReleaseGate(updated);
      setNotice("Test Lead muafiyeti kaydedildi.");
      setError("");
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        const updated = createPreviewReleaseWaiver(
          activeRelease,
          reason,
          user.username,
          expandedMetrics,
          defects,
        );
        setReleaseGate(updated);
        setAnalyticsPreviewMode(true);
        setNotice("Test Lead muafiyeti yerel önizleme deposuna kaydedildi.");
        setError("");
      } else {
        setError(formatErrorMessage(err, "Muafiyet kaydedilemedi."));
      }
    } finally {
      setGateSaving(false);
    }
  }

  async function handleDeleteWaiver() {
    const activeRelease = releases.find((r) => r.id === selectedReleaseId);
    if (!activeRelease || !expandedMetrics) return;
    setGateSaving(true);
    try {
      const updated = await api.deleteReleaseWaiver(activeRelease.id);
      setReleaseGate(updated);
      setNotice("Test Lead muafiyeti kaldırıldı.");
      setError("");
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        const updated = deletePreviewReleaseWaiver(
          activeRelease,
          expandedMetrics,
          defects,
        );
        setReleaseGate(updated);
        setAnalyticsPreviewMode(true);
        setNotice("Test Lead muafiyeti yerel önizleme deposundan kaldırıldı.");
        setError("");
      } else {
        setError(formatErrorMessage(err, "Muafiyet kaldırılamadı."));
      }
    } finally {
      setGateSaving(false);
    }
  }

  const defectColumns: DataTableColumn<Defect>[] = [
    {
      key: "id",
      header: "#",
      render: (d) => (
        <Link to={`/defects/${d.id}`} className="table-link">
          #{d.id}
        </Link>
      ),
    },
    {
      key: "title",
      header: "Başlık",
      render: (d) => (
        <Link to={`/defects/${d.id}`} className="table-link">
          {d.title}
        </Link>
      ),
    },
    { key: "test_case", header: "Test Vakası", render: (d) => d.test_case ?? "—" },
    { key: "severity", header: "Önem", render: (d) => <StatusBadge text={d.severity} /> },
    { key: "status", header: "Durum", render: (d) => <StatusBadge text={d.status} /> },
    {
      key: "allowed",
      header: "Geçiş",
      render: (d) =>
        d.allowed.length > 0 ? (
          d.allowed.map((to) => (
            <button
              key={to}
              type="button"
              disabled={transitioningId === d.id}
              onClick={() => void move(d.id, to)}
            >
              → {to}
            </button>
          ))
        ) : (
          <span className="hint">—</span>
        ),
    },
    {
      key: "detail",
      header: "Geçmiş",
      render: (d) => (
        <Link to={`/defects/${d.id}`} className="detail-link">
          Detay &amp; Zaman Çizelgesi
        </Link>
      ),
    },
  ];

  return (
    <>
      <ErrorAlert message={error} onDismiss={() => setError("")} />

      {notice && (
        <section className="role-notice" role="status">
          <span>{notice}</span>
          <button type="button" className="secondary-btn" onClick={() => setNotice("")}>
            Kapat
          </button>
        </section>
      )}

      {metrics && (
        <section className="metrics">
          {[
            ["Toplam Test", metrics.total_tests],
            ["Koşum Oranı", `${metrics.execution_rate}%`],
            ["Başarı Oranı", `${metrics.pass_rate}%`],
            ["Açık Defect", metrics.open_defects],
          ].map(([label, value]) => (
            <div className="card" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </section>
      )}

      {expandedMetrics && (
        <section>
          <div className="section-header">
            <div>
              <h2>Grafikli Metrik Paneli (R5)</h2>
              <p className="section-desc">
                ISO/IEC/IEEE 29119-2 · Test İzleme ve Kontrol · Koşum trendi, defect burn-up ve
                önem dağılımı
              </p>
            </div>
            {releases.length > 0 && (
              <div className="filter-group">
                <label htmlFor="dashboard-release-select">Sürüm:</label>
                <select
                  id="dashboard-release-select"
                  value={selectedReleaseId ? String(selectedReleaseId) : ""}
                  onChange={(e) =>
                    setSelectedReleaseId(e.target.value ? Number(e.target.value) : null)
                  }
                >
                  {releases.map((r) => (
                    <option key={r.id} value={String(r.id)}>
                      {r.version}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {analyticsPreviewMode && (
            <div className="info-banner" style={{ marginBottom: 12 }} role="note">
              <strong>Önizleme Modu (PLN-18 / PLN-24 Backend Bekleniyor):</strong>{" "}
              Genişletilmiş metrikler ve sürüm çıkış kapısı değerleri mevcut canlı{" "}
              <code>/api/defects</code>, <code>/api/requirements</code>,{" "}
              <code>/api/test-cases</code> verileri ile önizleme test koşumlarından
              hesaplanır.
            </div>
          )}

          <div className="sub-metrics">
            <div className="sub-metric-item">
              <span>Gereksinim Kapsamı</span>
              <strong>{expandedMetrics.requirement_coverage}%</strong>
            </div>
            <div className="sub-metric-item">
              <span>Yeniden Açılma Oranı</span>
              <strong>{expandedMetrics.reopen_rate}%</strong>
            </div>
            <div className="sub-metric-item">
              <span>Ort. Defect Yaşı</span>
              <strong>{expandedMetrics.avg_defect_age_hours ?? "—"} sa</strong>
            </div>
            <div className="sub-metric-item">
              <span>Ort. Çözüm Süresi</span>
              <strong>{expandedMetrics.avg_resolution_hours ?? "—"} sa</strong>
            </div>
          </div>

          <MetricsCharts metrics={expandedMetrics} />
        </section>
      )}

      <ReleaseGateCard
        gate={releaseGate}
        user={user}
        saving={gateSaving}
        onUpdateStatus={handleUpdateReleaseStatus}
        onUpdateCriteria={handleUpdateExitCriteria}
        onCreateWaiver={handleCreateWaiver}
        onDeleteWaiver={handleDeleteWaiver}
        showManageLink
      />

      <section>
        <div className="section-header">
          <h2>Test Vakaları</h2>
          <div className="row-actions">
            <Link to="/test-cases" className="detail-link">
              Test Vakası / Suite &amp; Matris Yönetimi →
            </Link>
            <Link to="/test-runs" className="detail-link">
              Test Koşumu Başlat / Yürüt →
            </Link>
            <Link to="/test-plans" className="detail-link">
              IEEE 829 Test Planları &amp; HTML/PDF →
            </Link>
          </div>
        </div>
        <DataTable
          columns={TEST_CASE_COLUMNS}
          rows={tests}
          getRowKey={(t) => t.id}
          emptyMessage="Kayıtlı test vakası bulunamadı."
          ariaLabel="Test Vakaları"
        />
      </section>

      <section>
        <h2>Defect&apos;ler</h2>
        {!user && (
          <p className="hint role-inline-hint">
            Defect oluşturmak ve durum geçişi yapmak için{" "}
            <Link to="/login">giriş yapın</Link>.
          </p>
        )}
        {user && !canCreateDefect && (
          <p className="hint role-inline-hint">
            Yeni defect kaydı yalnızca Admin, Test Lead veya Tester rolleri tarafından
            oluşturulabilir.
          </p>
        )}

        {canCreateDefect && (
          <form onSubmit={addDefect} noValidate>
            <FormField id="defect-title" label="Başlık" required error={formErrors.title}>
              <input
                id="defect-title"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  if (formErrors.title) {
                    setFormErrors((prev) => ({ ...prev, title: undefined }));
                  }
                }}
                placeholder="Yeni defect başlığı (en az 3 karakter)"
                aria-invalid={Boolean(formErrors.title)}
                aria-describedby={formErrors.title ? "defect-title-error" : undefined}
              />
            </FormField>

            <FormField id="defect-severity" label="Önem" required error={formErrors.severity}>
              <select
                id="defect-severity"
                value={severity}
                onChange={(e) => {
                  setSeverity(e.target.value);
                  if (formErrors.severity) {
                    setFormErrors((prev) => ({ ...prev, severity: undefined }));
                  }
                }}
                aria-invalid={Boolean(formErrors.severity)}
                aria-describedby={formErrors.severity ? "defect-severity-error" : undefined}
              >
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField id="defect-test-case" label="Test Vakası" error={formErrors.testCase}>
              <select
                id="defect-test-case"
                value={testCase}
                onChange={(e) => {
                  setTestCase(e.target.value);
                  if (formErrors.testCase) {
                    setFormErrors((prev) => ({ ...prev, testCase: undefined }));
                  }
                }}
                aria-invalid={Boolean(formErrors.testCase)}
                aria-describedby={formErrors.testCase ? "defect-test-case-error" : undefined}
              >
                <option value="">Bağlı değil</option>
                {tests.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.id} · {t.title}
                  </option>
                ))}
              </select>
            </FormField>

            <div className="form-actions">
              <button type="submit" disabled={submitting}>
                {submitting ? "Ekleniyor..." : "Ekle"}
              </button>
            </div>
          </form>
        )}

        <DataTable
          columns={defectColumns}
          rows={defects}
          getRowKey={(d) => d.id}
          emptyMessage="Kayıtlı defect bulunamadı."
          ariaLabel="Defect Listesi"
        />
        <p className="hint">Yaşam döngüsü: Open → In Progress → Resolved → Closed (+ Reopen)</p>
      </section>
    </>
  );
}

export default function App() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) return;
    api
      .me()
      .then((u) => setUser(u))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          clearStoredToken();
        }
        setUser(null);
      });
  }, []);

  useEffect(() => {
    function handleAuthExpired() {
      setUser(null);
      navigate("/login");
    }
    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
  }, [navigate]);

  function handleLogout() {
    clearStoredToken();
    setUser(null);
  }

  return (
    <>
      <header>
        <div className="header-inner">
          <div>
            <h1>SDS-06 · Agile Test and Defect Tracking System</h1>
            <p>ISO/IEC/IEEE 12207 · IEEE 829 · ISO/IEC/IEEE 29119-2 / 29119-3</p>
          </div>

          <div className="auth-bar">
            {user ? (
              <>
                <span className="auth-user">
                  <strong>{user.username}</strong> <StatusBadge text={user.role} />
                </span>
                <button
                  type="button"
                  className="header-btn"
                  onClick={handleLogout}
                >
                  Çıkış Yap
                </button>
              </>
            ) : (
              <Link to="/login" className="header-btn">
                Giriş Yap
              </Link>
            )}
          </div>
        </div>

        <nav className="top-nav" aria-label="Ana Gezinme">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            Panel &amp; Metrikler
          </NavLink>
          <NavLink
            to="/test-cases"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            Test Vakaları &amp; Matris
          </NavLink>
          <NavLink
            to="/test-runs"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            Test Koşumları
          </NavLink>
          <NavLink
            to="/test-plans"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            Test Planları
          </NavLink>
          <NavLink
            to="/releases"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            Sürüm Yönetimi
          </NavLink>
          <NavLink
            to="/projects"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            Projeler &amp; Gereksinimler
          </NavLink>
          <NavLink
            to="/login"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            Giriş / Rol Seçimi
          </NavLink>
          <NavLink to="/junit-imports" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>JUnit Raporları</NavLink>
        </nav>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<DashboardView user={user} />} />
          <Route path="/test-cases" element={<TestCasesPage user={user} />} />
          <Route path="/junit-imports" element={<JUnitImportsPage user={user} />} />
          <Route path="/test-runs" element={<TestRunsPage user={user} />} />
          <Route path="/test-plans" element={<TestPlansPage user={user} />} />
          <Route path="/defects/:id" element={<DefectDetailPage user={user} />} />
          <Route path="/releases" element={<ReleasesPage user={user} />} />
          <Route path="/projects" element={<ProjectsPage user={user} />} />
          <Route
            path="/login"
            element={<LoginPage user={user} onLogin={setUser} onLogout={handleLogout} />}
          />
        </Routes>
      </main>

      <footer>
        İstanbul Kültür Üniversitesi · Software Development with Standards · v0.1
      </footer>
    </>
  );
}
