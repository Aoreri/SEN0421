import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, formatErrorMessage, Role, setStoredToken, User } from "../api";
import { ErrorAlert } from "../components/ErrorAlert";
import { FormField } from "../components/FormField";
import { StatusBadge } from "../components/StatusBadge";
import { hasFormErrors, LoginFormErrors, validateLoginForm } from "../validation";

const DEMO_USERS: { username: string; role: Role; summary: string }[] = [
  { username: "admin", role: "Admin", summary: "Tüm katalog, izlenebilirlik ve defect geçiş yetkileri" },
  { username: "testlead", role: "Test Lead", summary: "Proje/sürüm/gereksinim yönetimi, defect doğrulama ve kapatma" },
  { username: "tester", role: "Tester", summary: "Defect oluşturma, izlenebilirlik eşleştirme, Resolved → Closed / Reopen" },
  { username: "developer", role: "Developer", summary: "Open → In Progress → Resolved defect durum geçişleri" },
];

export type LoginPageProps = {
  user: User | null;
  onLogin: (user: User) => void;
  onLogout: () => void;
};

export function LoginPage({ user, onLogin, onLogout }: LoginPageProps) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [formErrors, setFormErrors] = useState<LoginFormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const validationErrors = validateLoginForm({ username, password });
    setFormErrors(validationErrors);
    if (hasFormErrors(validationErrors)) {
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.login(username, password);
      setStoredToken(res.access_token);
      onLogin(res.user);
      setError("");
      navigate("/");
    } catch (err) {
      setError(formatErrorMessage(err, "Giriş yapılırken bir hata oluştu."));
    } finally {
      setSubmitting(false);
    }
  }

  function fillDemoUser(demoUsername: string) {
    setUsername(demoUsername);
    setPassword("demo1234");
    setFormErrors({});
    setError("");
  }

  return (
    <>
      <ErrorAlert message={error} onDismiss={() => setError("")} />

      {user && (
        <section className="session-card">
          <div>
            <strong>Aktif Oturum:</strong> {user.username}{" "}
            <StatusBadge text={user.role} />
          </div>
          <button type="button" className="secondary-btn" onClick={onLogout}>
            Çıkış Yap
          </button>
        </section>
      )}

      <section>
        <h2>Kullanıcı Girişi (JWT Kimlik Doğrulama)</h2>
        <p className="section-desc">
          Rol tabanlı işlemleri (defect oluşturma, durum geçişleri, proje/sürüm/gereksinim yönetimi
          ve izlenebilirlik) gerçekleştirmek için giriş yapın.
        </p>

        <form onSubmit={handleSubmit} noValidate>
          <FormField id="login-username" label="Kullanıcı Adı" required error={formErrors.username}>
            <input
              id="login-username"
              autoComplete="username"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (formErrors.username) {
                  setFormErrors((prev) => ({ ...prev, username: undefined }));
                }
              }}
              placeholder="Örn: tester"
              aria-invalid={Boolean(formErrors.username)}
              aria-describedby={formErrors.username ? "login-username-error" : undefined}
            />
          </FormField>

          <FormField id="login-password" label="Parola" required error={formErrors.password}>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (formErrors.password) {
                  setFormErrors((prev) => ({ ...prev, password: undefined }));
                }
              }}
              placeholder="Parolanızı girin"
              aria-invalid={Boolean(formErrors.password)}
              aria-describedby={formErrors.password ? "login-password-error" : undefined}
            />
          </FormField>

          <div className="form-actions">
            <button type="submit" disabled={submitting}>
              {submitting ? "Giriş yapılıyor..." : "Giriş Yap"}
            </button>
          </div>
        </form>
      </section>

      <section>
        <h2>Demo Hesapları (Varsayılan Parola: <code>demo1234</code>)</h2>
        <table aria-label="Demo Kullanıcıları">
          <thead>
            <tr>
              <th>Kullanıcı Adı</th>
              <th>Rol</th>
              <th>Yetki Özeti</th>
              <th>Hızlı Seçim</th>
            </tr>
          </thead>
          <tbody>
            {DEMO_USERS.map((u) => (
              <tr key={u.username}>
                <td>
                  <code>{u.username}</code>
                </td>
                <td>
                  <StatusBadge text={u.role} />
                </td>
                <td>{u.summary}</td>
                <td>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => fillDemoUser(u.username)}
                  >
                    Bilgileri Doldur
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
