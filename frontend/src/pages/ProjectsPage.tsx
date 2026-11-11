import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  formatErrorMessage,
  Project,
  Release,
  Requirement,
  TestCase,
  User,
} from "../api";
import { DataTable, DataTableColumn } from "../components/DataTable";
import { ErrorAlert } from "../components/ErrorAlert";
import { FormField } from "../components/FormField";
import { StatusBadge } from "../components/StatusBadge";
import {
  hasFormErrors,
  ProjectFormErrors,
  ReleaseFormErrors,
  RequirementFormErrors,
  validateProjectForm,
  validateReleaseForm,
  validateRequirementForm,
} from "../validation";

export type ProjectsPageProps = {
  user: User | null;
};

export function ProjectsPage({ user }: ProjectsPageProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [releases, setReleases] = useState<Release[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [error, setError] = useState("");
  const [filterProjectId, setFilterProjectId] = useState<string>("all");

  // Project form state
  const [editingProjectId, setEditingProjectId] = useState<number | null>(null);
  const [projectName, setProjectName] = useState("");
  const [projectDesc, setProjectDesc] = useState("");
  const [projectErrors, setProjectErrors] = useState<ProjectFormErrors>({});
  const [savingProject, setSavingProject] = useState(false);

  // Release form state
  const [editingReleaseId, setEditingReleaseId] = useState<number | null>(null);
  const [releaseProjectId, setReleaseProjectId] = useState("");
  const [releaseVersion, setReleaseVersion] = useState("");
  const [releaseErrors, setReleaseErrors] = useState<ReleaseFormErrors>({});
  const [savingRelease, setSavingRelease] = useState(false);

  // Requirement form state
  const [editingRequirementId, setEditingRequirementId] = useState<string | null>(null);
  const [reqId, setReqId] = useState("");
  const [reqProjectId, setReqProjectId] = useState("");
  const [reqTitle, setReqTitle] = useState("");
  const [reqDesc, setReqDesc] = useState("");
  const [reqErrors, setReqErrors] = useState<RequirementFormErrors>({});
  const [savingReq, setSavingReq] = useState(false);

  // Traceability editor state
  const [traceRequirement, setTraceRequirement] = useState<Requirement | null>(null);
  const [selectedTestCases, setSelectedTestCases] = useState<string[]>([]);
  const [savingTrace, setSavingTrace] = useState(false);

  const canWriteCatalog =
    user !== null && (user.role === "Admin" || user.role === "Test Lead");
  const canEditTraceability =
    user !== null &&
    (user.role === "Admin" || user.role === "Test Lead" || user.role === "Tester");

  const loadAll = useCallback(async () => {
    try {
      const [p, rel, req, tc] = await Promise.all([
        api.projects(),
        api.releases(),
        api.requirements(),
        api.testCases(),
      ]);
      setProjects(p);
      setReleases(rel);
      setRequirements(req);
      setTestCases(tc);
      if (p.length > 0) {
        const defaultPid = String(p[0].id);
        setReleaseProjectId((prev) => prev || defaultPid);
        setReqProjectId((prev) => prev || defaultPid);
      }
      setError("");
    } catch (err) {
      setError(
        formatErrorMessage(
          err,
          "Proje ve gereksinim verileri yüklenemedi. Önce backend'i başlatın.",
        ),
      );
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  function projectNameById(projectId: number): string {
    const found = projects.find((p) => p.id === projectId);
    return found ? found.name : `#${projectId}`;
  }

  // --- Project handlers ---
  function startEditProject(p: Project) {
    setEditingProjectId(p.id);
    setProjectName(p.name);
    setProjectDesc(p.description);
    setProjectErrors({});
  }

  function resetProjectForm() {
    setEditingProjectId(null);
    setProjectName("");
    setProjectDesc("");
    setProjectErrors({});
  }

  async function submitProject(e: FormEvent) {
    e.preventDefault();
    const errs = validateProjectForm({ name: projectName, description: projectDesc });
    setProjectErrors(errs);
    if (hasFormErrors(errs)) return;

    setSavingProject(true);
    try {
      if (editingProjectId !== null) {
        await api.updateProject(editingProjectId, projectName, projectDesc);
      } else {
        await api.createProject(projectName, projectDesc);
      }
      resetProjectForm();
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, "Proje kaydedilirken bir hata oluştu."));
    } finally {
      setSavingProject(false);
    }
  }

  async function removeProject(id: number) {
    try {
      await api.deleteProject(id);
      if (editingProjectId === id) resetProjectForm();
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, "Proje silinirken bir hata oluştu."));
    }
  }

  // --- Release handlers ---
  function startEditRelease(r: Release) {
    setEditingReleaseId(r.id);
    setReleaseProjectId(String(r.project_id));
    setReleaseVersion(r.version);
    setReleaseErrors({});
  }

  function resetReleaseForm() {
    setEditingReleaseId(null);
    setReleaseProjectId(projects[0] ? String(projects[0].id) : "");
    setReleaseVersion("");
    setReleaseErrors({});
  }

  async function submitRelease(e: FormEvent) {
    e.preventDefault();
    const errs = validateReleaseForm({
      projectId: releaseProjectId,
      version: releaseVersion,
    });
    setReleaseErrors(errs);
    if (hasFormErrors(errs)) return;

    setSavingRelease(true);
    try {
      const pid = Number(releaseProjectId);
      if (editingReleaseId !== null) {
        await api.updateRelease(editingReleaseId, pid, releaseVersion);
      } else {
        await api.createRelease(pid, releaseVersion);
      }
      resetReleaseForm();
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, "Sürüm kaydedilirken bir hata oluştu."));
    } finally {
      setSavingRelease(false);
    }
  }

  async function removeRelease(id: number) {
    try {
      await api.deleteRelease(id);
      if (editingReleaseId === id) resetReleaseForm();
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, "Sürüm silinirken bir hata oluştu."));
    }
  }

  // --- Requirement handlers ---
  function startEditRequirement(r: Requirement) {
    setEditingRequirementId(r.id);
    setReqId(r.id);
    setReqProjectId(String(r.project_id));
    setReqTitle(r.title);
    setReqDesc(r.description);
    setReqErrors({});
  }

  function resetRequirementForm() {
    setEditingRequirementId(null);
    setReqId("");
    setReqProjectId(projects[0] ? String(projects[0].id) : "");
    setReqTitle("");
    setReqDesc("");
    setReqErrors({});
  }

  async function submitRequirement(e: FormEvent) {
    e.preventDefault();
    const errs = validateRequirementForm(
      {
        id: reqId,
        projectId: reqProjectId,
        title: reqTitle,
        description: reqDesc,
      },
      editingRequirementId === null,
    );
    setReqErrors(errs);
    if (hasFormErrors(errs)) return;

    setSavingReq(true);
    try {
      const pid = Number(reqProjectId);
      if (editingRequirementId !== null) {
        await api.updateRequirement(editingRequirementId, pid, reqTitle, reqDesc);
      } else {
        await api.createRequirement(reqId, pid, reqTitle, reqDesc);
      }
      resetRequirementForm();
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, "Gereksinim kaydedilirken bir hata oluştu."));
    } finally {
      setSavingReq(false);
    }
  }

  async function removeRequirement(id: string) {
    try {
      await api.deleteRequirement(id);
      if (editingRequirementId === id) resetRequirementForm();
      if (traceRequirement?.id === id) setTraceRequirement(null);
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, "Gereksinim silinirken bir hata oluştu."));
    }
  }

  // --- Traceability handlers ---
  function openTraceabilityEditor(r: Requirement) {
    setTraceRequirement(r);
    setSelectedTestCases(r.test_cases);
  }

  function toggleTestCaseSelection(tcId: string) {
    setSelectedTestCases((prev) =>
      prev.includes(tcId) ? prev.filter((id) => id !== tcId) : [...prev, tcId],
    );
  }

  async function saveTraceability(e: FormEvent) {
    e.preventDefault();
    if (!traceRequirement) return;
    setSavingTrace(true);
    try {
      await api.setRequirementTestCases(traceRequirement.id, selectedTestCases);
      setTraceRequirement(null);
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, "İzlenebilirlik bağlantıları güncellenemedi."));
    } finally {
      setSavingTrace(false);
    }
  }

  const filteredRequirements =
    filterProjectId === "all"
      ? requirements
      : requirements.filter((r) => String(r.project_id) === filterProjectId);

  const projectColumns: DataTableColumn<Project>[] = [
    { key: "id", header: "ID", render: (p) => p.id },
    { key: "name", header: "Proje Adı", render: (p) => <strong>{p.name}</strong> },
    { key: "description", header: "Açıklama", render: (p) => p.description || "—" },
    ...(canWriteCatalog
      ? [
          {
            key: "actions",
            header: "İşlemler",
            render: (p: Project) => (
              <div className="row-actions">
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => startEditProject(p)}
                >
                  Düzenle
                </button>
                <button
                  type="button"
                  className="danger-btn"
                  onClick={() => void removeProject(p.id)}
                >
                  Sil
                </button>
              </div>
            ),
          },
        ]
      : []),
  ];

  const releaseColumns: DataTableColumn<Release>[] = [
    { key: "id", header: "ID", render: (r) => r.id },
    { key: "project", header: "Proje", render: (r) => projectNameById(r.project_id) },
    { key: "version", header: "Sürüm", render: (r) => <StatusBadge text={r.version} /> },
    ...(canWriteCatalog
      ? [
          {
            key: "actions",
            header: "İşlemler",
            render: (r: Release) => (
              <div className="row-actions">
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => startEditRelease(r)}
                >
                  Düzenle
                </button>
                <button
                  type="button"
                  className="danger-btn"
                  onClick={() => void removeRelease(r.id)}
                >
                  Sil
                </button>
              </div>
            ),
          },
        ]
      : []),
  ];

  const requirementColumns: DataTableColumn<Requirement>[] = [
    { key: "id", header: "Kod", render: (r) => <strong>{r.id}</strong> },
    { key: "project", header: "Proje", render: (r) => projectNameById(r.project_id) },
    { key: "title", header: "Başlık", render: (r) => r.title },
    { key: "description", header: "Açıklama", render: (r) => r.description || "—" },
    {
      key: "test_cases",
      header: "Bağlı Test Vakaları",
      render: (r) =>
        r.test_cases.length > 0 ? (
          <div className="badge-list">
            {r.test_cases.map((tc) => (
              <StatusBadge key={tc} text={tc} />
            ))}
          </div>
        ) : (
          <span className="hint">Bağlı test yok</span>
        ),
    },
    ...(canEditTraceability || canWriteCatalog
      ? [
          {
            key: "actions",
            header: "İşlemler",
            render: (r: Requirement) => (
              <div className="row-actions">
                {canEditTraceability && (
                  <button
                    type="button"
                    onClick={() => openTraceabilityEditor(r)}
                  >
                    Test Bağla
                  </button>
                )}
                {canWriteCatalog && (
                  <>
                    <button
                      type="button"
                      className="secondary-btn"
                      onClick={() => startEditRequirement(r)}
                    >
                      Düzenle
                    </button>
                    <button
                      type="button"
                      className="danger-btn"
                      onClick={() => void removeRequirement(r.id)}
                    >
                      Sil
                    </button>
                  </>
                )}
              </div>
            ),
          },
        ]
      : []),
  ];

  return (
    <>
      <ErrorAlert message={error} onDismiss={() => setError("")} />

      {!user && (
        <section className="role-notice">
          <span>
            Proje, sürüm ve gereksinim kayıtlarını görüntülüyorsunuz. Düzenleme veya izlenebilirlik
            eşleştirmesi yapmak için giriş yapın.
          </span>
          <Link to="/login" className="btn-link">
            Giriş Ekranına Git
          </Link>
        </section>
      )}

      {user && !canWriteCatalog && (
        <section className="role-notice">
          <span>
            Aktif rolünüz (<StatusBadge text={user.role} />):{" "}
            {canEditTraceability
              ? "Gereksinim ↔ Test Vakası izlenebilirlik bağlantılarını güncelleyebilirsiniz. Proje/sürüm/gereksinim ekleme ve silme işlemleri Admin veya Test Lead rolü gerektirir."
              : "Katalog kayıtlarını salt okunur görüntülüyorsunuz."}
          </span>
        </section>
      )}

      <section>
        <h2>Projeler</h2>
        {canWriteCatalog && (
          <form onSubmit={submitProject} noValidate>
            <FormField
              id="project-name"
              label={editingProjectId !== null ? `Proje Adı (#${editingProjectId})` : "Proje Adı"}
              required
              error={projectErrors.name}
            >
              <input
                id="project-name"
                value={projectName}
                onChange={(e) => {
                  setProjectName(e.target.value);
                  if (projectErrors.name) {
                    setProjectErrors((prev) => ({ ...prev, name: undefined }));
                  }
                }}
                placeholder="Örn: SDS-06"
                aria-invalid={Boolean(projectErrors.name)}
              />
            </FormField>

            <FormField
              id="project-desc"
              label="Açıklama"
              error={projectErrors.description}
            >
              <input
                id="project-desc"
                value={projectDesc}
                onChange={(e) => {
                  setProjectDesc(e.target.value);
                  if (projectErrors.description) {
                    setProjectErrors((prev) => ({ ...prev, description: undefined }));
                  }
                }}
                placeholder="Proje açıklaması (isteğe bağlı)"
                aria-invalid={Boolean(projectErrors.description)}
              />
            </FormField>

            <div className="form-actions">
              <button type="submit" disabled={savingProject}>
                {savingProject
                  ? "Kaydediliyor..."
                  : editingProjectId !== null
                    ? "Projeyi Güncelle"
                    : "Proje Ekle"}
              </button>
              {editingProjectId !== null && (
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={resetProjectForm}
                >
                  İptal
                </button>
              )}
            </div>
          </form>
        )}

        <DataTable
          columns={projectColumns}
          rows={projects}
          getRowKey={(p) => p.id}
          emptyMessage="Kayıtlı proje bulunamadı."
          ariaLabel="Projeler"
        />
      </section>

      <section>
        <h2>Sürümler (Releases)</h2>
        {canWriteCatalog && (
          <form onSubmit={submitRelease} noValidate>
            <FormField
              id="release-project"
              label="Proje"
              required
              error={releaseErrors.projectId}
            >
              <select
                id="release-project"
                value={releaseProjectId}
                onChange={(e) => {
                  setReleaseProjectId(e.target.value);
                  if (releaseErrors.projectId) {
                    setReleaseErrors((prev) => ({ ...prev, projectId: undefined }));
                  }
                }}
                aria-invalid={Boolean(releaseErrors.projectId)}
              >
                <option value="">Proje seçin</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} (#{p.id})
                  </option>
                ))}
              </select>
            </FormField>

            <FormField
              id="release-version"
              label={editingReleaseId !== null ? `Sürüm (#${editingReleaseId})` : "Sürüm"}
              required
              error={releaseErrors.version}
            >
              <input
                id="release-version"
                value={releaseVersion}
                onChange={(e) => {
                  setReleaseVersion(e.target.value);
                  if (releaseErrors.version) {
                    setReleaseErrors((prev) => ({ ...prev, version: undefined }));
                  }
                }}
                placeholder="Örn: v0.1.0"
                aria-invalid={Boolean(releaseErrors.version)}
              />
            </FormField>

            <div className="form-actions">
              <button type="submit" disabled={savingRelease}>
                {savingRelease
                  ? "Kaydediliyor..."
                  : editingReleaseId !== null
                    ? "Sürümü Güncelle"
                    : "Sürüm Ekle"}
              </button>
              {editingReleaseId !== null && (
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={resetReleaseForm}
                >
                  İptal
                </button>
              )}
            </div>
          </form>
        )}

        <DataTable
          columns={releaseColumns}
          rows={releases}
          getRowKey={(r) => r.id}
          emptyMessage="Kayıtlı sürüm bulunamadı."
          ariaLabel="Sürümler"
        />
      </section>

      <section>
        <div className="section-header">
          <div>
            <h2>Gereksinimler ve Test Vakası İzlenebilirliği (R1–R8)</h2>
            <p className="hint">
              ISO/IEC/IEEE 29119-2 Test Tasarımı ve Gerçekleştirme · Gereksinim ↔ Test Vakası
              çoka-çok izlenebilirlik matrisi
            </p>
          </div>
          <div className="filter-group">
            <label htmlFor="req-project-filter">Proje Filtresi:</label>
            <select
              id="req-project-filter"
              value={filterProjectId}
              onChange={(e) => setFilterProjectId(e.target.value)}
            >
              <option value="all">Tüm Projeler</option>
              {projects.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {canWriteCatalog && (
          <form onSubmit={submitRequirement} noValidate>
            <FormField
              id="req-id"
              label="Gereksinim Kodu"
              required
              error={reqErrors.id}
            >
              <input
                id="req-id"
                value={reqId}
                disabled={editingRequirementId !== null}
                onChange={(e) => {
                  setReqId(e.target.value);
                  if (reqErrors.id) {
                    setReqErrors((prev) => ({ ...prev, id: undefined }));
                  }
                }}
                placeholder="Örn: R9"
                aria-invalid={Boolean(reqErrors.id)}
              />
            </FormField>

            <FormField
              id="req-project"
              label="Proje"
              required
              error={reqErrors.projectId}
            >
              <select
                id="req-project"
                value={reqProjectId}
                onChange={(e) => {
                  setReqProjectId(e.target.value);
                  if (reqErrors.projectId) {
                    setReqErrors((prev) => ({ ...prev, projectId: undefined }));
                  }
                }}
                aria-invalid={Boolean(reqErrors.projectId)}
              >
                <option value="">Proje seçin</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} (#{p.id})
                  </option>
                ))}
              </select>
            </FormField>

            <FormField
              id="req-title"
              label="Başlık"
              required
              error={reqErrors.title}
            >
              <input
                id="req-title"
                value={reqTitle}
                onChange={(e) => {
                  setReqTitle(e.target.value);
                  if (reqErrors.title) {
                    setReqErrors((prev) => ({ ...prev, title: undefined }));
                  }
                }}
                placeholder="Gereksinim başlığı"
                aria-invalid={Boolean(reqErrors.title)}
              />
            </FormField>

            <FormField
              id="req-desc"
              label="Açıklama"
              error={reqErrors.description}
            >
              <input
                id="req-desc"
                value={reqDesc}
                onChange={(e) => {
                  setReqDesc(e.target.value);
                  if (reqErrors.description) {
                    setReqErrors((prev) => ({ ...prev, description: undefined }));
                  }
                }}
                placeholder="Detaylı açıklama (isteğe bağlı)"
                aria-invalid={Boolean(reqErrors.description)}
              />
            </FormField>

            <div className="form-actions">
              <button type="submit" disabled={savingReq}>
                {savingReq
                  ? "Kaydediliyor..."
                  : editingRequirementId !== null
                    ? "Gereksinimi Güncelle"
                    : "Gereksinim Ekle"}
              </button>
              {editingRequirementId !== null && (
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={resetRequirementForm}
                >
                  İptal
                </button>
              )}
            </div>
          </form>
        )}

        {traceRequirement && canEditTraceability && (
          <form className="trace-panel" onSubmit={saveTraceability}>
            <div className="trace-panel-header">
              <strong>
                {traceRequirement.id} · {traceRequirement.title} — Test Vakası Bağlantıları
              </strong>
              <span>Bağlanacak test vakalarını seçin:</span>
            </div>
            <div className="trace-checkbox-grid">
              {testCases.map((tc) => {
                const checked = selectedTestCases.includes(tc.id);
                return (
                  <label key={tc.id} className="trace-checkbox-item">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleTestCaseSelection(tc.id)}
                    />
                    <span>
                      <strong>{tc.id}</strong> · {tc.title}
                    </span>
                    <StatusBadge text={tc.status} />
                  </label>
                );
              })}
            </div>
            <div className="row-actions">
              <button type="submit" disabled={savingTrace}>
                {savingTrace ? "Kaydediliyor..." : "Bağlantıları Kaydet"}
              </button>
              <button
                type="button"
                className="secondary-btn"
                onClick={() => setTraceRequirement(null)}
              >
                İptal
              </button>
            </div>
          </form>
        )}

        <DataTable
          columns={requirementColumns}
          rows={filteredRequirements}
          getRowKey={(r) => r.id}
          emptyMessage="Kayıtlı gereksinim bulunamadı."
          ariaLabel="Gereksinimler"
        />
      </section>
    </>
  );
}
