import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  formatErrorMessage,
  Project,
  Release,
  TestPlan,
  TestPlanSnapshot,
  TestPlanSnapshotSummary,
  TestPlanStatus,
  User,
} from "../api";
import { DataTable, DataTableColumn } from "../components/DataTable";
import { ErrorAlert } from "../components/ErrorAlert";
import { FormField } from "../components/FormField";
import { StatusBadge } from "../components/StatusBadge";
import {
  hasFormErrors,
  TestPlanFormErrors,
  validateTestPlanForm,
} from "../validation";

export type TestPlansPageProps = {
  user: User | null;
};

// Yalnızca backend API'sinin (backend/app/test_plans.py VALID_STATUS_TRANSITIONS)
// izin verdiği durum geçişleri gösterilir:
// Draft -> In Review, In Review -> Draft | Approved, Approved -> Draft
const ALLOWED_PLAN_TRANSITIONS: Record<TestPlanStatus, readonly TestPlanStatus[]> = {
  Draft: ["In Review"],
  "In Review": ["Draft", "Approved"],
  Approved: ["Draft"],
};

function formatIsoTime(iso: string | null): string {
  if (!iso) return "—";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleString("tr-TR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function TestPlansPage({ user }: TestPlansPageProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [releases, setReleases] = useState<Release[]>([]);
  const [plans, setPlans] = useState<TestPlan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [selectedPlanDetail, setSelectedPlanDetail] = useState<TestPlan | null>(null);
  const [previewSnapshot, setPreviewSnapshot] = useState<TestPlanSnapshot | null>(null);

  const [filterProjectId, setFilterProjectId] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [transitioningId, setTransitioningId] = useState<number | null>(null);
  const [creatingSnapshotId, setCreatingSnapshotId] = useState<number | null>(null);
  const [loadingSnapshotId, setLoadingSnapshotId] = useState<number | null>(null);
  const [error, setError] = useState("");

  async function handleDownload(planId: number, format: "html" | "pdf", snapshotId?: number) {
    try {
      await api.downloadTestPlan(planId, format, snapshotId);
    } catch (err) {
      setError(formatErrorMessage(err, "Test Plan indirilemedi."));
    }
  }
  const [notice, setNotice] = useState("");

  // Form state (create & draft/in-review edit)
  const [editingPlanId, setEditingPlanId] = useState<number | null>(null);
  const [planProjectId, setPlanProjectId] = useState("");
  const [planReleaseId, setPlanReleaseId] = useState("");
  const [planVersion, setPlanVersion] = useState("");
  const [planTitle, setPlanTitle] = useState("");
  const [planScope, setPlanScope] = useState("");
  const [planApproach, setPlanApproach] = useState("");
  const [planPassFailCriteria, setPlanPassFailCriteria] = useState("");
  const [planEnvironment, setPlanEnvironment] = useState("");
  const [planScheduleRisks, setPlanScheduleRisks] = useState("");
  const [formErrors, setFormErrors] = useState<TestPlanFormErrors>({});

  const canManagePlans =
    user !== null && (user.role === "Admin" || user.role === "Test Lead");
  const canTakeSnapshot =
    user !== null &&
    (user.role === "Admin" || user.role === "Test Lead" || user.role === "Tester");

  const loadDetail = useCallback(async (planId: number) => {
    try {
      const detail = await api.getTestPlan(planId);
      setSelectedPlanDetail(detail);
    } catch (err) {
      setError(formatErrorMessage(err, "Test Plan detayı ve sürüm geçmişi yüklenemedi."));
    }
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [projs, rels, loadedPlans] = await Promise.all([
        api.projects(),
        api.releases(),
        api.testPlans(),
      ]);
      setProjects(projs);
      setReleases(rels);
      setPlans(loadedPlans);
      if (projs.length > 0) {
        setPlanProjectId((prev) => prev || String(projs[0].id));
      }
      setSelectedPlanId((prev) => {
        if (prev && loadedPlans.some((p) => p.id === prev)) return prev;
        return loadedPlans[0]?.id ?? null;
      });
      setError("");
    } catch (err) {
      setError(
        formatErrorMessage(
          err,
          "Test Plan verileri yüklenemedi. Önce backend'i başlatın.",
        ),
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll, user]);

  useEffect(() => {
    if (selectedPlanId !== null) {
      void loadDetail(selectedPlanId);
    } else {
      setSelectedPlanDetail(null);
    }
    setPreviewSnapshot(null);
  }, [selectedPlanId, loadDetail]);

  const projectNames = useMemo(
    () => new Map(projects.map((p) => [p.id, p.name])),
    [projects],
  );

  const releaseLabels = useMemo(
    () => new Map(releases.map((r) => [r.id, r.version])),
    [releases],
  );

  const filteredPlans = useMemo(() => {
    if (filterProjectId === "all") return plans;
    return plans.filter((p) => String(p.project_id) === filterProjectId);
  }, [plans, filterProjectId]);

  const activePlan = useMemo(() => {
    if (selectedPlanDetail && selectedPlanDetail.id === selectedPlanId) {
      return selectedPlanDetail;
    }
    return plans.find((p) => p.id === selectedPlanId) ?? null;
  }, [plans, selectedPlanId, selectedPlanDetail]);

  function resetForm() {
    setEditingPlanId(null);
    setPlanProjectId(projects[0] ? String(projects[0].id) : "");
    setPlanReleaseId("");
    setPlanVersion("");
    setPlanTitle("");
    setPlanScope("");
    setPlanApproach("");
    setPlanPassFailCriteria("");
    setPlanEnvironment("");
    setPlanScheduleRisks("");
    setFormErrors({});
  }

  function startEditPlan(plan: TestPlan) {
    if (plan.status === "Approved") return;
    setEditingPlanId(plan.id);
    setPlanProjectId(String(plan.project_id));
    setPlanReleaseId(plan.release_id ? String(plan.release_id) : "");
    setPlanVersion(plan.version);
    setPlanTitle(plan.title);
    setPlanScope(plan.scope);
    setPlanApproach(plan.approach);
    setPlanPassFailCriteria(plan.pass_fail_criteria);
    setPlanEnvironment(plan.environment);
    setPlanScheduleRisks(plan.schedule_risks);
    setFormErrors({});
    setSelectedPlanId(plan.id);
  }

  async function handleSubmitPlan(e: FormEvent) {
    e.preventDefault();
    const errs = validateTestPlanForm({
      projectId: planProjectId,
      version: planVersion,
      title: planTitle,
      scope: planScope,
      approach: planApproach,
      passFailCriteria: planPassFailCriteria,
      environment: planEnvironment,
      scheduleRisks: planScheduleRisks,
    });
    setFormErrors(errs);
    if (hasFormErrors(errs)) return;

    const payload = {
      project_id: Number(planProjectId),
      release_id: planReleaseId ? Number(planReleaseId) : null,
      version: planVersion.trim(),
      title: planTitle.trim(),
      scope: planScope.trim(),
      approach: planApproach.trim(),
      pass_fail_criteria: planPassFailCriteria.trim(),
      environment: planEnvironment.trim(),
      schedule_risks: planScheduleRisks.trim(),
    };

    setSaving(true);
    try {
      if (editingPlanId !== null) {
        const updated = await api.updateTestPlan(editingPlanId, payload);
        setSelectedPlanId(updated.id);
        setSelectedPlanDetail(updated);
        setNotice(`"${updated.title}" (${updated.version}) taslağı güncellendi.`);
      } else {
        const created = await api.createTestPlan(payload);
        setSelectedPlanId(created.id);
        setSelectedPlanDetail(created);
        setNotice(`"${created.title}" (${created.version}) Test Plan taslağı oluşturuldu.`);
      }
      resetForm();
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, "Test Plan kaydedilirken bir hata oluştu."));
    } finally {
      setSaving(false);
    }
  }

  async function handleTransitionStatus(plan: TestPlan, nextStatus: TestPlanStatus) {
    if (!canManagePlans) return;
    setTransitioningId(plan.id);
    try {
      const updated = await api.updateTestPlanStatus(plan.id, nextStatus);
      if (editingPlanId === plan.id && nextStatus === "Approved") {
        resetForm();
      }
      setSelectedPlanId(updated.id);
      setSelectedPlanDetail(updated);
      setNotice(
        `Test Plan #${updated.id} (${updated.version}) durumu "${plan.status}" → "${updated.status}" olarak güncellendi.`,
      );
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, "Test Plan durum geçişi yapılamadı."));
    } finally {
      setTransitioningId(null);
    }
  }

  async function handleDeletePlan(plan: TestPlan) {
    if (!canManagePlans || plan.status === "Approved") return;
    if (
      !window.confirm(
        `"${plan.title}" (${plan.version}) Test Plan kaydı silinsin mi? Bu işlem geri alınamaz.`,
      )
    ) {
      return;
    }
    try {
      await api.deleteTestPlan(plan.id);
      if (editingPlanId === plan.id) resetForm();
      if (selectedPlanId === plan.id) {
        setSelectedPlanId(null);
        setSelectedPlanDetail(null);
      }
      setNotice(`"${plan.title}" (${plan.version}) Test Plan kaydı silindi.`);
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, "Test Plan silinirken bir hata oluştu."));
    }
  }

  async function handleCreateSnapshot(plan: TestPlan) {
    if (!canTakeSnapshot) return;
    setCreatingSnapshotId(plan.id);
    try {
      const snap = await api.createTestPlanSnapshot(plan.id);
      setNotice(
        `Test Plan #${plan.id} (${snap.version}) için Snapshot #${snap.id} (${snap.status}) kaydedildi.`,
      );
      setError("");
      await loadAll();
      await loadDetail(plan.id);
    } catch (err) {
      setError(formatErrorMessage(err, "Test Plan anlık görüntüsü (snapshot) alınamadı."));
    } finally {
      setCreatingSnapshotId(null);
    }
  }

  async function handleViewSnapshot(planId: number, snapshotId: number) {
    if (previewSnapshot?.id === snapshotId) {
      setPreviewSnapshot(null);
      return;
    }
    setLoadingSnapshotId(snapshotId);
    try {
      const snap = await api.getTestPlanSnapshot(planId, snapshotId);
      setPreviewSnapshot(snap);
      setError("");
    } catch (err) {
      setError(formatErrorMessage(err, "Snapshot içeriği yüklenemedi."));
    } finally {
      setLoadingSnapshotId(null);
    }
  }

  const planColumns: DataTableColumn<TestPlan>[] = [
    { key: "id", header: "#", render: (p) => <strong>#{p.id}</strong> },
    {
      key: "project_release",
      header: "Proje / Sürüm",
      render: (p) => {
        const proj = projectNames.get(p.project_id) ?? `#${p.project_id}`;
        const rel = p.release_id ? releaseLabels.get(p.release_id) : null;
        return rel ? `${proj} · ${rel}` : `${proj} · Genel`;
      },
    },
    { key: "version", header: "Plan Sürümü", render: (p) => <StatusBadge text={p.version} /> },
    { key: "title", header: "Başlık", render: (p) => <strong>{p.title}</strong> },
    { key: "status", header: "Durum", render: (p) => <StatusBadge text={p.status} /> },
    {
      key: "transitions",
      header: "Durum Geçişi (API)",
      render: (p) => {
        const allowed = ALLOWED_PLAN_TRANSITIONS[p.status] ?? [];
        if (!canManagePlans) {
          return (
            <span className="hint">
              {allowed.map((to) => `→ ${to}`).join(", ") || "—"}
            </span>
          );
        }
        return (
          <div className="row-actions">
            {allowed.map((to) => (
              <button
                key={to}
                type="button"
                disabled={transitioningId === p.id}
                onClick={() => void handleTransitionStatus(p, to)}
              >
                → {to}
              </button>
            ))}
          </div>
        );
      },
    },
    {
      key: "snapshots",
      header: "Sürüm Geçmişi",
      render: (p) => <span className="badge">{p.snapshot_count} snapshot</span>,
    },
    {
      key: "export",
      header: "HTML / PDF İndir",
      render: (p) => (
        <div className="row-actions">
          <button type="button" className="secondary-btn" onClick={() => void handleDownload(p.id, "html")}>
            HTML
          </button>
          <button type="button" className="secondary-btn" onClick={() => void handleDownload(p.id, "pdf")}>
            PDF İndir
          </button>
        </div>
      ),
    },
    {
      key: "actions",
      header: "İşlemler",
      render: (p) => (
        <div className="row-actions">
          <button
            type="button"
            className={p.id === selectedPlanId ? "secondary-btn" : ""}
            onClick={() => setSelectedPlanId(p.id)}
          >
            {p.id === selectedPlanId ? "Seçili" : "Detay & Geçmiş"}
          </button>
          {canManagePlans && (
            <>
              <button
                type="button"
                className="secondary-btn"
                disabled={p.status === "Approved"}
                title={
                  p.status === "Approved"
                    ? "Onaylanmış (Approved) Test Plan düzenlenemez; önce Draft durumuna alın"
                    : undefined
                }
                onClick={() => startEditPlan(p)}
              >
                Taslağı Düzenle
              </button>
              <button
                type="button"
                className="danger-btn"
                disabled={p.status === "Approved"}
                title={
                  p.status === "Approved"
                    ? "Onaylanmış (Approved) Test Plan silinemez"
                    : undefined
                }
                onClick={() => void handleDeletePlan(p)}
              >
                Sil
              </button>
            </>
          )}
        </div>
      ),
    },
  ];

  const snapshotColumns: DataTableColumn<TestPlanSnapshotSummary>[] = [
    { key: "id", header: "Snapshot #", render: (s) => <strong>#{s.id}</strong> },
    { key: "version", header: "Plan Sürümü", render: (s) => <StatusBadge text={s.version} /> },
    { key: "status", header: "Alındığı Durum", render: (s) => <StatusBadge text={s.status} /> },
    { key: "generated_by", header: "Üreten", render: (s) => s.generated_by },
    {
      key: "generated_at",
      header: "Tarih",
      render: (s) => <span className="timeline-time">{formatIsoTime(s.generated_at)}</span>,
    },
    {
      key: "actions",
      header: "Çıktı & İndirme",
      render: (s) => (
        <div className="row-actions">
          <button type="button" className="secondary-btn" onClick={() => void handleDownload(s.test_plan_id, "html", s.id)}>
            HTML Görüntüle
          </button>
          <button type="button" className="secondary-btn" onClick={() => void handleDownload(s.test_plan_id, "pdf", s.id)}>
            PDF İndir
          </button>
          <button
            type="button"
            className="secondary-btn"
            disabled={loadingSnapshotId === s.id}
            onClick={() => void handleViewSnapshot(s.test_plan_id, s.id)}
          >
            {previewSnapshot?.id === s.id
              ? "Önizlemeyi Kapat"
              : loadingSnapshotId === s.id
                ? "Yükleniyor..."
                : "İçerik Özeti"}
          </button>
        </div>
      ),
    },
  ];

  const snapshots = selectedPlanDetail?.snapshots ?? [];

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

      {!user && (
        <section className="role-notice">
          <span>
            IEEE 829 / ISO/IEC/IEEE 29119-3 Test Plan kayıtlarını görüntülüyorsunuz ve HTML/PDF
            olarak indirebilirsiniz. Taslak oluşturmak, düzenlemek veya durum geçişi yapmak için
            giriş yapın.
          </span>
          <Link to="/login" className="btn-link">
            Giriş Ekranına Git
          </Link>
        </section>
      )}

      {user && !canManagePlans && (
        <section className="role-notice">
          <span>
            Aktif rolünüz (<StatusBadge text={user.role} />):{" "}
            {canTakeSnapshot
              ? "Test Plan anlık görüntüsü (snapshot) alabilir ve HTML/PDF indirebilirsiniz. Taslak oluşturma, düzenleme ve Draft → In Review → Approved durum geçişleri Admin veya Test Lead rolü gerektirir."
              : "Test Plan kayıtlarını salt okunur görüntülüyorsunuz ve HTML/PDF indirebilirsiniz."}
          </span>
        </section>
      )}

      {canManagePlans && (
        <section>
          <div className="section-header">
            <div>
              <h2>
                {editingPlanId !== null
                  ? `Test Plan Taslağını Düzenle (#${editingPlanId})`
                  : "Yeni IEEE 829 Test Plan Taslağı Oluştur"}
              </h2>
              <p className="section-desc">
                IEEE 829 Test Plan · ISO/IEC/IEEE 29119-3 Test Plan (R1, R3) · Yeni planlar{" "}
                <strong>Draft</strong> durumunda başlar; <strong>Approved</strong> durumundaki
                planlar tekrar <strong>Draft</strong> durumuna alınmadan düzenlenemez veya
                silinemez.
              </p>
            </div>
            {editingPlanId !== null && (
              <button type="button" className="secondary-btn" onClick={resetForm}>
                Düzenlemeyi İptal Et
              </button>
            )}
          </div>

          <form onSubmit={(e) => void handleSubmitPlan(e)} noValidate className="stacked-form">
            <div className="form-grid">
              <FormField
                id="plan-project"
                label="Proje"
                required
                error={formErrors.projectId}
              >
                <select
                  id="plan-project"
                  value={planProjectId}
                  onChange={(e) => {
                    const nextPid = e.target.value;
                    setPlanProjectId(nextPid);
                    setPlanReleaseId((prevRel) => {
                      if (!prevRel) return "";
                      const rel = releases.find((r) => String(r.id) === prevRel);
                      return rel && String(rel.project_id) === nextPid ? prevRel : "";
                    });
                    if (formErrors.projectId) {
                      setFormErrors((prev) => ({ ...prev, projectId: undefined }));
                    }
                  }}
                  aria-invalid={Boolean(formErrors.projectId)}
                >
                  <option value="">Proje seçin</option>
                  {projects.map((p) => (
                    <option key={p.id} value={String(p.id)}>
                      {p.name} (#{p.id})
                    </option>
                  ))}
                </select>
              </FormField>

              <FormField id="plan-release" label="Hedef Sürüm (Opsiyonel)">
                <select
                  id="plan-release"
                  value={planReleaseId}
                  onChange={(e) => setPlanReleaseId(e.target.value)}
                >
                  <option value="">Genel (Sürüme bağlı değil)</option>
                  {releases
                    .filter((r) => !planProjectId || String(r.project_id) === planProjectId)
                    .map((r) => (
                      <option key={r.id} value={String(r.id)}>
                        {r.version} ({r.status})
                      </option>
                    ))}
                </select>
              </FormField>

              <FormField
                id="plan-version"
                label="Plan Sürüm Numarası"
                required
                error={formErrors.version}
              >
                <input
                  id="plan-version"
                  value={planVersion}
                  onChange={(e) => {
                    setPlanVersion(e.target.value);
                    if (formErrors.version) {
                      setFormErrors((prev) => ({ ...prev, version: undefined }));
                    }
                  }}
                  placeholder="Örn: v1.0 veya 0.2-draft"
                  aria-invalid={Boolean(formErrors.version)}
                />
              </FormField>

              <FormField
                id="plan-title"
                label="Test Plan Başlığı"
                required
                error={formErrors.title}
              >
                <input
                  id="plan-title"
                  value={planTitle}
                  onChange={(e) => {
                    setPlanTitle(e.target.value);
                    if (formErrors.title) {
                      setFormErrors((prev) => ({ ...prev, title: undefined }));
                    }
                  }}
                  placeholder="Örn: SDS-06 Sürüm 1.0 Master Test Planı"
                  aria-invalid={Boolean(formErrors.title)}
                />
              </FormField>
            </div>

            <div className="form-grid">
              <FormField
                id="plan-scope"
                label="1. Kapsam (Test Items & Features to be Tested)"
                error={formErrors.scope}
              >
                <textarea
                  id="plan-scope"
                  rows={3}
                  value={planScope}
                  onChange={(e) => {
                    setPlanScope(e.target.value);
                    if (formErrors.scope) {
                      setFormErrors((prev) => ({ ...prev, scope: undefined }));
                    }
                  }}
                  placeholder="Test edilecek modüller, özellikler ve kapsam dışı bırakılanlar..."
                />
              </FormField>

              <FormField
                id="plan-approach"
                label="2. Test Yaklaşımı (Approach)"
                error={formErrors.approach}
              >
                <textarea
                  id="plan-approach"
                  rows={3}
                  value={planApproach}
                  onChange={(e) => {
                    setPlanApproach(e.target.value);
                    if (formErrors.approach) {
                      setFormErrors((prev) => ({ ...prev, approach: undefined }));
                    }
                  }}
                  placeholder="Birim, entegrasyon, kabul testleri ve doğrulama stratejisi..."
                />
              </FormField>
            </div>

            <div className="form-grid">
              <FormField
                id="plan-criteria"
                label="3. Kabul / Red ve Giriş / Çıkış Kriterleri (Pass/Fail Criteria)"
                error={formErrors.passFailCriteria}
              >
                <textarea
                  id="plan-criteria"
                  rows={3}
                  value={planPassFailCriteria}
                  onChange={(e) => {
                    setPlanPassFailCriteria(e.target.value);
                    if (formErrors.passFailCriteria) {
                      setFormErrors((prev) => ({ ...prev, passFailCriteria: undefined }));
                    }
                  }}
                  placeholder="Örn: Başarı oranı >= %80, açık Critical defect = 0, gereksinim kapsamı >= %80..."
                />
              </FormField>

              <FormField
                id="plan-environment"
                label="4. Test Ortamı ve Çıktılar (Environment & Deliverables)"
                error={formErrors.environment}
              >
                <textarea
                  id="plan-environment"
                  rows={3}
                  value={planEnvironment}
                  onChange={(e) => {
                    setPlanEnvironment(e.target.value);
                    if (formErrors.environment) {
                      setFormErrors((prev) => ({ ...prev, environment: undefined }));
                    }
                  }}
                  placeholder="PostgreSQL 16, FastAPI, React/Vite, GitHub Actions CI ortamı..."
                />
              </FormField>
            </div>

            <FormField
              id="plan-schedule-risks"
              label="5. Takvim, Sorumluluklar ve Riskler (Schedule, Responsibilities & Risks)"
              error={formErrors.scheduleRisks}
            >
              <textarea
                id="plan-schedule-risks"
                rows={2}
                value={planScheduleRisks}
                onChange={(e) => {
                  setPlanScheduleRisks(e.target.value);
                  if (formErrors.scheduleRisks) {
                    setFormErrors((prev) => ({ ...prev, scheduleRisks: undefined }));
                  }
                }}
                placeholder="Sprint takvimi, roller ve RSK kayıtlarına referanslar..."
              />
            </FormField>

            <div className="row-actions">
              <button type="submit" disabled={saving}>
                {saving
                  ? "Kaydediliyor..."
                  : editingPlanId !== null
                    ? "Test Plan Taslağını Güncelle"
                    : "Test Plan Taslağı Oluştur"}
              </button>
              {editingPlanId !== null && (
                <button type="button" className="secondary-btn" onClick={resetForm}>
                  İptal
                </button>
              )}
            </div>
          </form>
        </section>
      )}

      <section>
        <div className="section-header">
          <div>
            <h2>Kayıtlı Test Planları (IEEE 829 / ISO/IEC/IEEE 29119-3)</h2>
            <p className="section-desc">
              Yaşam döngüsü: <strong>Draft → In Review → Approved</strong> (Onaylı planı yeniden
              düzenlemek için <strong>Approved → Draft</strong> geçişi kullanılır). Yalnızca
              API&apos;nin izin verdiği durum geçişleri gösterilir.
            </p>
          </div>
          <div className="filter-group">
            <label htmlFor="plan-project-filter">Proje Filtresi:</label>
            <select
              id="plan-project-filter"
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

        {loading && plans.length === 0 ? (
          <p className="hint">Yükleniyor...</p>
        ) : (
          <DataTable
            columns={planColumns}
            rows={filteredPlans}
            getRowKey={(p) => p.id}
            emptyMessage="Kayıtlı Test Plan bulunamadı."
            ariaLabel="Test Planları"
          />
        )}
      </section>

      {activePlan && (
        <section>
          <div className="section-header">
            <div>
              <h2>
                Test Plan Detayı &amp; Sürüm Geçmişi: #{activePlan.id} · {activePlan.title}
              </h2>
              <p className="section-desc">
                Proje:{" "}
                <strong>
                  {projectNames.get(activePlan.project_id) ?? `#${activePlan.project_id}`}
                </strong>{" "}
                · Hedef Sürüm:{" "}
                <strong>
                  {activePlan.release_id
                    ? (releaseLabels.get(activePlan.release_id) ?? `#${activePlan.release_id}`)
                    : "Genel"}
                </strong>{" "}
                · Plan Sürümü: <StatusBadge text={activePlan.version} /> · Durum:{" "}
                <StatusBadge text={activePlan.status} /> · Oluşturan:{" "}
                <strong>{activePlan.created_by}</strong> ({formatIsoTime(activePlan.created_at)})
              </p>
            </div>

            <div className="row-actions">
              <button type="button" className="secondary-btn" onClick={() => void handleDownload(activePlan.id, "html")}>
            Canlı HTML Görüntüle
          </button>
              <button type="button" className="secondary-btn" onClick={() => void handleDownload(activePlan.id, "pdf")}>
            Canlı PDF İndir
          </button>
              {canTakeSnapshot && (
                <button
                  type="button"
                  disabled={creatingSnapshotId === activePlan.id}
                  onClick={() => void handleCreateSnapshot(activePlan)}
                >
                  {creatingSnapshotId === activePlan.id
                    ? "Snapshot Alınıyor..."
                    : "Anlık Görüntü (Snapshot) Kaydet"}
                </button>
              )}
            </div>
          </div>

          <div className="transition-box" style={{ marginBottom: 14 }}>
            <div className="inline-controls">
              <div>
                <h3>İzin Verilen Durum Geçişleri (Draft → In Review → Approved)</h3>
                <p className="hint" style={{ marginTop: 2 }}>
                  API kuralları gereği doğrudan <code>Draft → Approved</code> geçişi yapılamaz;
                  önce <code>In Review</code> durumuna geçirilmelidir.
                </p>
              </div>
              <div className="row-actions">
                {(ALLOWED_PLAN_TRANSITIONS[activePlan.status] ?? []).map((to) => (
                  <button
                    key={to}
                    type="button"
                    disabled={!canManagePlans || transitioningId === activePlan.id}
                    onClick={() => void handleTransitionStatus(activePlan, to)}
                  >
                    {activePlan.status} → {to}
                  </button>
                ))}
                {canManagePlans && activePlan.status !== "Approved" && (
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => startEditPlan(activePlan)}
                  >
                    Taslağı Formda Düzenle
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">1. Kapsam (Scope)</span>
              <p className="expected-text">{activePlan.scope || "Belirtilmedi."}</p>
            </div>
            <div className="detail-item">
              <span className="detail-label">2. Test Yaklaşımı (Approach)</span>
              <p className="expected-text">{activePlan.approach || "Belirtilmedi."}</p>
            </div>
            <div className="detail-item">
              <span className="detail-label">3. Kabul / Red Kriterleri (Pass/Fail Criteria)</span>
              <p className="expected-text">
                {activePlan.pass_fail_criteria || "Belirtilmedi."}
              </p>
            </div>
            <div className="detail-item">
              <span className="detail-label">4. Test Ortamı ve Çıktılar (Environment)</span>
              <p className="expected-text">{activePlan.environment || "Belirtilmedi."}</p>
            </div>
            <div className="detail-item">
              <span className="detail-label">5. Takvim ve Riskler (Schedule &amp; Risks)</span>
              <p className="expected-text">{activePlan.schedule_risks || "Belirtilmedi."}</p>
            </div>
          </div>

          <h3>Sürüm Geçmişi ve Anlık Görüntüler (Snapshots)</h3>
          <p className="section-desc">
            Her snapshot alındığı andaki Test Plan metnini, gereksinim izlenebilirliğini, test
            vakalarını, defect kayıtlarını ve metrik özetini değiştirilemez olarak saklar ve o
            sürüme ait HTML / PDF indirilmesini sağlar.
          </p>

          <DataTable
            columns={snapshotColumns}
            rows={snapshots}
            getRowKey={(s) => s.id}
            emptyMessage="Bu Test Plan için henüz kaydedilmiş bir sürüm anlık görüntüsü (snapshot) bulunmuyor."
            ariaLabel="Test Plan Sürüm Geçmişi"
          />

          {previewSnapshot && previewSnapshot.test_plan_id === activePlan.id && (
            <div className="case-detail-drawer">
              <div className="section-header" style={{ marginBottom: 8 }}>
                <div>
                  <strong>
                    Snapshot #{previewSnapshot.id} Özeti · Sürüm {previewSnapshot.version} (
                    {previewSnapshot.status})
                  </strong>
                  <p className="hint" style={{ marginTop: 2 }}>
                    Üreten: {previewSnapshot.generated_by} ·{" "}
                    {formatIsoTime(previewSnapshot.generated_at)}
                  </p>
                </div>
                <div className="row-actions">
                  <button type="button" className="secondary-btn" onClick={() => void handleDownload(activePlan.id, "html", previewSnapshot.id)}>
            Tam HTML Raporu Aç
          </button>
                  <button type="button" className="secondary-btn" onClick={() => void handleDownload(activePlan.id, "pdf", previewSnapshot.id)}>
            PDF İndir
          </button>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => setPreviewSnapshot(null)}
                  >
                    Kapat
                  </button>
                </div>
              </div>
              <pre
                style={{
                  margin: 0,
                  padding: 10,
                  background: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: 6,
                  fontSize: ".8rem",
                  maxHeight: 240,
                  overflow: "auto",
                }}
              >
                {JSON.stringify(previewSnapshot.payload, null, 2)}
              </pre>
            </div>
          )}
        </section>
      )}
    </>
  );
}
