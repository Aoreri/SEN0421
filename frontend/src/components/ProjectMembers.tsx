import { FormEvent, useEffect, useState } from "react";
import { api, formatErrorMessage, Project, User } from "../api";
import { DataTable, DataTableColumn } from "./DataTable";
import { ErrorAlert } from "./ErrorAlert";
import { FormField } from "./FormField";
import { StatusBadge } from "./StatusBadge";

export type ProjectMembersProps = {
  projects: Project[];
};

/** PLN-40: Admin ve Test Lead, Tester ve Developer hesaplarını projelere ekler veya çıkarır. */
export function ProjectMembers({ projects }: ProjectMembersProps) {
  const [projectId, setProjectId] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [members, setMembers] = useState<User[]>([]);
  const [userId, setUserId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const activeId = projectId || (projects[0] ? String(projects[0].id) : "");

  useEffect(() => {
    api
      .users()
      .then(setUsers)
      .catch((err) => setError(formatErrorMessage(err, "Kullanıcılar yüklenemedi.")));
  }, []);

  useEffect(() => {
    if (!activeId) {
      setMembers([]);
      return;
    }
    api
      .projectMembers(Number(activeId))
      .then(setMembers)
      .catch((err) => setError(formatErrorMessage(err, "Proje üyeleri yüklenemedi.")));
  }, [activeId]);

  // Admin ve Test Lead tüm projelere zaten erişir; yalnızca Tester/Developer eklenebilir.
  const candidates = users.filter(
    (u) =>
      (u.role === "Tester" || u.role === "Developer") && !members.some((m) => m.id === u.id),
  );

  async function change(action: () => Promise<User[]>, fallback: string) {
    setBusy(true);
    try {
      setMembers(await action());
      setUserId("");
      setError("");
    } catch (err) {
      setError(formatErrorMessage(err, fallback));
    } finally {
      setBusy(false);
    }
  }

  function addMember(e: FormEvent) {
    e.preventDefault();
    if (!activeId || !userId) return;
    void change(
      () => api.addProjectMember(Number(activeId), Number(userId)),
      "Üye eklenemedi.",
    );
  }

  const columns: DataTableColumn<User>[] = [
    { key: "username", header: "Kullanıcı Adı", render: (u) => <code>{u.username}</code> },
    { key: "role", header: "Rol", render: (u) => <StatusBadge text={u.role} /> },
    {
      key: "actions",
      header: "İşlemler",
      render: (u) => (
        <button
          type="button"
          className="danger-btn"
          disabled={busy}
          onClick={() =>
            void change(
              () => api.removeProjectMember(Number(activeId), u.id),
              "Üye çıkarılamadı.",
            )
          }
        >
          Projeden Çıkar
        </button>
      ),
    },
  ];

  return (
    <section>
      <h2>Proje Üyeleri</h2>
      <p className="hint">
        Tester ve Developer hesapları yalnızca üye oldukları projeleri görür. Admin ve Test Lead
        tüm projelere erişir.
      </p>
      <ErrorAlert message={error} onDismiss={() => setError("")} />
      <form onSubmit={addMember} noValidate>
        <FormField id="member-project" label="Proje">
          <select
            id="member-project"
            value={activeId}
            onChange={(e) => setProjectId(e.target.value)}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </FormField>
        <FormField id="member-user" label="Kullanıcı">
          <select id="member-user" value={userId} onChange={(e) => setUserId(e.target.value)}>
            <option value="">Seçin</option>
            {candidates.map((u) => (
              <option key={u.id} value={u.id}>
                {u.username} ({u.role})
              </option>
            ))}
          </select>
        </FormField>
        <div className="form-actions">
          <button type="submit" disabled={busy || !activeId || !userId}>
            Projeye Ekle
          </button>
        </div>
      </form>
      <DataTable
        columns={columns}
        rows={members}
        getRowKey={(u) => u.id}
        emptyMessage="Bu projede üye yok; Tester ve Developer hesapları projeyi göremez."
        ariaLabel="Proje Üyeleri"
      />
    </section>
  );
}
