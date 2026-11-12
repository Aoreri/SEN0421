import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import {
  api,
  ApiError,
  AUTH_EXPIRED_EVENT,
  clearStoredToken,
  Defect,
  formatErrorMessage,
  getStoredToken,
  Metrics,
  SEVERITIES,
  TestCase,
  User,
} from "./api";
import { DataTable, DataTableColumn } from "./components/DataTable";
import { ErrorAlert } from "./components/ErrorAlert";
import { FormField } from "./components/FormField";
import { StatusBadge } from "./components/StatusBadge";
import { DefectDetailPage } from "./pages/DefectDetailPage";
import { LoginPage } from "./pages/LoginPage";
import { ProjectsPage } from "./pages/ProjectsPage";
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
  const [tests, setTests] = useState<TestCase[]>([]);
  const [defects, setDefects] = useState<Defect[]>([]);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState("Medium");
  const [testCase, setTestCase] = useState("");
  const [formErrors, setFormErrors] = useState<DefectFormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [transitioningId, setTransitioningId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const canCreateDefect =
    user !== null &&
    (user.role === "Admin" || user.role === "Test Lead" || user.role === "Tester");

  const load = useCallback(async () => {
    try {
      const [m, t, d] = await Promise.all([api.metrics(), api.testCases(), api.defects()]);
      setMetrics(m);
      setTests(t);
      setDefects(d);
      setError("");
    } catch (err) {
      setError(
        formatErrorMessage(
          err,
          "Backend'e ulaşılamadı. Önce backend'i başlatın (README'ye bakın).",
        ),
      );
    }
  }, []);

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

      <section>
        <h2>Test Vakaları</h2>
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
            Panel &amp; Defect Takibi
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
        </nav>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<DashboardView user={user} />} />
          <Route path="/defects/:id" element={<DefectDetailPage user={user} />} />
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
