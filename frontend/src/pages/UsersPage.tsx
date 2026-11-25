import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, formatErrorMessage, Role, User } from "../api";
import { DataTable, DataTableColumn } from "../components/DataTable";
import { ErrorAlert } from "../components/ErrorAlert";
import { FormField } from "../components/FormField";
import { StatusBadge } from "../components/StatusBadge";

export type UsersPageProps = {
  user: User | null;
};

// Admin hesabı buradan açılamaz; sunucu da reddeder (PLN-40).
const CREATABLE_ROLES: Role[] = ["Test Lead", "Tester", "Developer"];

/** PLN-40: Admin kullanıcı hesabı oluşturur ve siler. */
export function UsersPage({ user }: UsersPageProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("Tester");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const isAdmin = user?.role === "Admin";

  const load = useCallback(async () => {
    if (!isAdmin) return;
    try {
      setUsers(await api.users());
    } catch (err) {
      setError(formatErrorMessage(err, "Kullanıcılar yüklenemedi."));
    }
  }, [isAdmin]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!isAdmin) {
    return (
      <section className="role-notice">
        <span>Kullanıcı hesaplarını yalnızca Admin yönetebilir.</span>
      </section>
    );
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (username.trim().length < 3 || password.length < 8) {
      setError("Kullanıcı adı en az 3, parola en az 8 karakter olmalıdır.");
      return;
    }
    setBusy(true);
    try {
      const created = await api.createUser(username, password, role);
      setNotice(
        `${created.username} oluşturuldu. Projeleri görebilmesi için Projeler ekranından projeye ekleyin.`,
      );
      setUsername("");
      setPassword("");
      setError("");
      await load();
    } catch (err) {
      setError(formatErrorMessage(err, "Kullanıcı oluşturulamadı."));
    } finally {
      setBusy(false);
    }
  }

  async function remove(target: User) {
    if (!window.confirm(`${target.username} hesabı silinsin mi?`)) return;
    try {
      await api.deleteUser(target.id);
      setNotice(`${target.username} silindi.`);
      setError("");
      await load();
    } catch (err) {
      setError(formatErrorMessage(err, "Kullanıcı silinemedi."));
    }
  }

  const columns: DataTableColumn<User>[] = [
    { key: "username", header: "Kullanıcı Adı", render: (u) => <code>{u.username}</code> },
    { key: "role", header: "Rol", render: (u) => <StatusBadge text={u.role} /> },
    {
      key: "actions",
      header: "İşlemler",
      render: (u) =>
        u.role === "Admin" ? (
          <span className="hint">—</span>
        ) : (
          <button type="button" className="danger-btn" onClick={() => void remove(u)}>
            Sil
          </button>
        ),
    },
  ];

  return (
    <>
      <ErrorAlert message={error} onDismiss={() => setError("")} />
      {notice && (
        <section className="role-notice" role="status">
          <span>{notice}</span>
        </section>
      )}
      <section>
        <h2>Kullanıcılar</h2>
        <p className="hint">
          Yeni hesaplar hiçbir projeyi görmez; Tester ve Developer hesaplarını Projeler ekranından
          projeye ekleyin. Admin hesabı oluşturulamaz.
        </p>
        <form onSubmit={submit} noValidate>
          <FormField id="new-username" label="Kullanıcı Adı" required>
            <input
              id="new-username"
              value={username}
              autoComplete="off"
              onChange={(e) => setUsername(e.target.value)}
            />
          </FormField>
          <FormField id="new-password" label="Parola" required>
            <input
              id="new-password"
              type="password"
              value={password}
              autoComplete="new-password"
              onChange={(e) => setPassword(e.target.value)}
            />
          </FormField>
          <FormField id="new-role" label="Rol" required>
            <select id="new-role" value={role} onChange={(e) => setRole(e.target.value as Role)}>
              {CREATABLE_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </FormField>
          <div className="form-actions">
            <button type="submit" disabled={busy}>
              {busy ? "Oluşturuluyor..." : "Kullanıcı Oluştur"}
            </button>
          </div>
        </form>
        <DataTable
          columns={columns}
          rows={users}
          getRowKey={(u) => u.id}
          emptyMessage="Kullanıcı bulunamadı."
          ariaLabel="Kullanıcılar"
        />
      </section>
    </>
  );
}
