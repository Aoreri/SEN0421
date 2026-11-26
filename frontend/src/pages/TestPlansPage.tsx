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
import { useLang, useT } from "../i18n";

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

function formatIsoTime(iso: string | null, lang: "tr" | "en"): string {
  if (!iso) return "—";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleString(lang === "tr" ? "tr-TR" : "en-GB", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function TestPlansPage({ user }: TestPlansPageProps) {
  const t = useT();
  const lang = useLang();
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
      setError(formatErrorMessage(err, t("Test Plan indirilemedi.")));
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
      setError(formatErrorMessage(err, t("Test Plan detayı ve sürüm geçmişi yüklenemedi.")));
    }
  }, [t]);

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
          t("Test Plan verileri yüklenemedi. Önce backend'i başlatın."),
        ),
      );
    } finally {
      setLoading(false);
    }
  }, [t]);

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
        setNotice(
          t("\"{title}\" ({version}) taslağı güncellendi.", {
            title: updated.title,
            version: updated.version,
          }),
        );
      } else {
        const created = await api.createTestPlan(payload);
        setSelectedPlanId(created.id);
        setSelectedPlanDetail(created);
        setNotice(
          t("\"{title}\" ({version}) Test Plan taslağı oluşturuldu.", {
            title: created.title,
            version: created.version,
          }),
        );
      }
      resetForm();
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, t("Test Plan kaydedilirken bir hata oluştu.")));
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
        t("Test Plan #{id} ({version}) durumu \"{from}\" → \"{to}\" olarak güncellendi.", {
          id: updated.id,
          version: updated.version,
          from: plan.status,
          to: updated.status,
        }),
      );
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, t("Test Plan durum geçişi yapılamadı.")));
    } finally {
      setTransitioningId(null);
    }
  }

  async function handleDeletePlan(plan: TestPlan) {
    if (!canManagePlans || plan.status === "Approved") return;
    if (
      !window.confirm(
        t("\"{title}\" ({version}) Test Plan kaydı silinsin mi? Bu işlem geri alınamaz.", {
          title: plan.title,
          version: plan.version,
        }),
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
      setNotice(
        t("\"{title}\" ({version}) Test Plan kaydı silindi.", {
          title: plan.title,
          version: plan.version,
        }),
      );
      setError("");
      await loadAll();
    } catch (err) {
      setError(formatErrorMessage(err, t("Test Plan silinirken bir hata oluştu.")));
    }
  }

  async function handleCreateSnapshot(plan: TestPlan) {
    if (!canTakeSnapshot) return;
    setCreatingSnapshotId(plan.id);
    try {
      const snap = await api.createTestPlanSnapshot(plan.id);
      setNotice(
        t("Test Plan #{id} ({version}) için Snapshot #{snapshot} ({status}) kaydedildi.", {
          id: plan.id,
          version: snap.version,
          snapshot: snap.id,
          status: snap.status,
        }),
      );
      setError("");
      await loadAll();
      await loadDetail(plan.id);
    } catch (err) {
      setError(formatErrorMessage(err, t("Test Plan anlık görüntüsü (snapshot) alınamadı.")));
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
      setError(formatErrorMessage(err, t("Snapshot içeriği yüklenemedi.")));
    } finally {
      setLoadingSnapshotId(null);
    }
  }

  const planColumns: DataTableColumn<TestPlan>[] = [
    { key: "id", header: "#", render: (p) => <strong>#{p.id}</strong> },
    {
      key: "project_release",
      header: t("Proje / Sürüm"),
      render: (p) => {
        const proj = projectNames.get(p.project_id) ?? `#${p.project_id}`;
        const rel = p.release_id ? releaseLabels.get(p.release_id) : null;
        return rel ? `${proj} · ${rel}` : `${proj} · ${t("Genel")}`;
      },
    },
    { key: "version", header: t("Plan Sürümü"), render: (p) => <StatusBadge text={p.version} /> },
    { key: "title", header: t("Başlık"), render: (p) => <strong>{p.title}</strong> },
    { key: "status", header: t("Durum"), render: (p) => <StatusBadge text={p.status} /> },
    {
      key: "transitions",
      header: t("Durum Geçişi (API)"),
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
      header: t("Sürüm Geçmişi"),
      render: (p) => (
        <span className="badge">{t("{count} snapshot", { count: p.snapshot_count })}</span>
      ),
    },
    {
      key: "export",
      header: t("HTML / PDF İndir"),
      render: (p) => (
        <div className="row-actions">
          <button type="button" className="secondary-btn" onClick={() => void handleDownload(p.id, "html")}>
            HTML
          </button>
          <button type="button" className="secondary-btn" onClick={() => void handleDownload(p.id, "pdf")}>
            {t("PDF İndir")}
          </button>
        </div>
      ),
    },
    {
      key: "actions",
      header: t("İşlemler"),
      render: (p) => (
        <div className="row-actions">
          <button
            type="button"
            className={p.id === selectedPlanId ? "secondary-btn" : ""}
            onClick={() => setSelectedPlanId(p.id)}
          >
            {p.id === selectedPlanId ? t("Seçili") : t("Detay & Geçmiş")}
          </button>
          {canManagePlans && (
            <>
              <button
                type="button"
                className="secondary-btn"
                disabled={p.status === "Approved"}
                title={
                  p.status === "Approved"
                    ? t(
                        "Onaylanmış (Approved) Test Plan düzenlenemez; önce Draft durumuna alın",
                      )
                    : undefined
                }
                onClick={() => startEditPlan(p)}
              >
                {t("Taslağı Düzenle")}
              </button>
              <button
                type="button"
                className="danger-btn"
                disabled={p.status === "Approved"}
                title={
                  p.status === "Approved"
                    ? t("Onaylanmış (Approved) Test Plan silinemez")
                    : undefined
                }
                onClick={() => void handleDeletePlan(p)}
              >
                {t("Sil")}
              </button>
            </>
          )}
        </div>
      ),
    },
  ];

  const snapshotColumns: DataTableColumn<TestPlanSnapshotSummary>[] = [
    { key: "id", header: "Snapshot #", render: (s) => <strong>#{s.id}</strong> },
    { key: "version", header: t("Plan Sürümü"), render: (s) => <StatusBadge text={s.version} /> },
    { key: "status", header: t("Alındığı Durum"), render: (s) => <StatusBadge text={s.status} /> },
    { key: "generated_by", header: t("Üreten"), render: (s) => s.generated_by },
    {
      key: "generated_at",
      header: t("Tarih"),
      render: (s) => (
        <span className="timeline-time">{formatIsoTime(s.generated_at, lang)}</span>
      ),
    },
    {
      key: "actions",
      header: t("Çıktı & İndirme"),
      render: (s) => (
        <div className="row-actions">
          <button type="button" className="secondary-btn" onClick={() => void handleDownload(s.test_plan_id, "html", s.id)}>
            {t("HTML Görüntüle")}
          </button>
          <button type="button" className="secondary-btn" onClick={() => void handleDownload(s.test_plan_id, "pdf", s.id)}>
            {t("PDF İndir")}
          </button>
          <button
            type="button"
            className="secondary-btn"
            disabled={loadingSnapshotId === s.id}
            onClick={() => void handleViewSnapshot(s.test_plan_id, s.id)}
          >
            {previewSnapshot?.id === s.id
              ? t("Önizlemeyi Kapat")
              : loadingSnapshotId === s.id
                ? t("Yükleniyor...")
                : t("İçerik Özeti")}
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
            {t("Kapat")}
          </button>
        </section>
      )}

      {!user && (
        <section className="role-notice">
          <span>
            {t(
              "IEEE 829 Test Plan kayıtlarını görüntülüyorsunuz ve HTML/PDF olarak indirebilirsiniz. Taslak oluşturmak, düzenlemek veya durum geçişi yapmak için giriş yapın.",
            )}
          </span>
          <Link to="/login" className="btn-link">
            {t("Giriş Ekranına Git")}
          </Link>
        </section>
      )}

      {user && !canManagePlans && (
        <section className="role-notice">
          <span>
            {t("Aktif rolünüz (")}
            <StatusBadge text={user.role} />
            {t("):")}{" "}
            {canTakeSnapshot
              ? t(
                  "Test Plan anlık görüntüsü (snapshot) alabilir ve HTML/PDF indirebilirsiniz. Taslak oluşturma, düzenleme ve Draft → In Review → Approved durum geçişleri Admin veya Test Lead rolü gerektirir.",
                )
              : t(
                  "Test Plan kayıtlarını salt okunur görüntülüyorsunuz ve HTML/PDF indirebilirsiniz.",
                )}
          </span>
        </section>
      )}

      {canManagePlans && (
        <section>
          <div className="section-header">
            <div>
              <h2>
                {editingPlanId !== null
                  ? t("Test Plan Taslağını Düzenle (#{id})", { id: editingPlanId })
                  : t("Yeni IEEE 829 Test Plan Taslağı Oluştur")}
              </h2>
              <p className="section-desc">
                {t("IEEE 829 Test Plan · Yeni planlar")} <strong>Draft</strong>{" "}
                {t("durumunda başlar;")} <strong>Approved</strong>{" "}
                {t("durumundaki planlar tekrar")} <strong>Draft</strong>{" "}
                {t("durumuna alınmadan düzenlenemez veya silinemez.")}
              </p>
            </div>
            {editingPlanId !== null && (
              <button type="button" className="secondary-btn" onClick={resetForm}>
                {t("Düzenlemeyi İptal Et")}
              </button>
            )}
          </div>

          <form onSubmit={(e) => void handleSubmitPlan(e)} noValidate className="stacked-form">
            <div className="form-grid">
              <FormField
                id="plan-project"
                label={t("Proje")}
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
                  <option value="">{t("Proje seçin")}</option>
                  {projects.map((p) => (
                    <option key={p.id} value={String(p.id)}>
                      {p.name} (#{p.id})
                    </option>
                  ))}
                </select>
              </FormField>

              <FormField id="plan-release" label={t("Hedef Sürüm (Opsiyonel)")}>
                <select
                  id="plan-release"
                  value={planReleaseId}
                  onChange={(e) => setPlanReleaseId(e.target.value)}
                >
                  <option value="">{t("Genel (Sürüme bağlı değil)")}</option>
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
                label={t("Plan Sürüm Numarası")}
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
                  placeholder={t("Örn: v1.0 veya 0.2-draft")}
                  aria-invalid={Boolean(formErrors.version)}
                />
              </FormField>

              <FormField
                id="plan-title"
                label={t("Test Plan Başlığı")}
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
                  placeholder={t("Örn: SDS-06 Sürüm 1.0 Master Test Planı")}
                  aria-invalid={Boolean(formErrors.title)}
                />
              </FormField>
            </div>

            <div className="form-grid">
              <FormField
                id="plan-scope"
                label={t("1. Kapsam (Test Items & Features to be Tested)")}
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
                  placeholder={t("Test edilecek modüller, özellikler ve kapsam dışı bırakılanlar...")}
                />
              </FormField>

              <FormField
                id="plan-approach"
                label={t("2. Test Yaklaşımı (Approach)")}
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
                  placeholder={t("Birim, entegrasyon, kabul testleri ve doğrulama stratejisi...")}
                />
              </FormField>
            </div>

            <div className="form-grid">
              <FormField
                id="plan-criteria"
                label={t("3. Kabul / Red ve Giriş / Çıkış Kriterleri (Pass/Fail Criteria)")}
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
                  placeholder={t(
                    "Örn: Başarı oranı >= %80, açık Critical defect = 0, gereksinim kapsamı >= %80...",
                  )}
                />
              </FormField>

              <FormField
                id="plan-environment"
                label={t("4. Test Ortamı ve Çıktılar (Environment & Deliverables)")}
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
                  placeholder={t("PostgreSQL 16, FastAPI, React/Vite, GitHub Actions CI ortamı...")}
                />
              </FormField>
            </div>

            <FormField
              id="plan-schedule-risks"
              label={t("5. Takvim, Sorumluluklar ve Riskler (Schedule, Responsibilities & Risks)")}
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
                placeholder={t("Sprint takvimi, roller ve RSK kayıtlarına referanslar...")}
              />
            </FormField>

            <div className="row-actions">
              <button type="submit" disabled={saving}>
                {saving
                  ? t("Kaydediliyor...")
                  : editingPlanId !== null
                    ? t("Test Plan Taslağını Güncelle")
                    : t("Test Plan Taslağı Oluştur")}
              </button>
              {editingPlanId !== null && (
                <button type="button" className="secondary-btn" onClick={resetForm}>
                  {t("İptal")}
                </button>
              )}
            </div>
          </form>
        </section>
      )}

      <section>
        <div className="section-header">
          <div>
            <h2>{t("Kayıtlı Test Planları")}</h2>
            <p className="section-desc">
              {t("Yaşam döngüsü:")} <strong>Draft → In Review → Approved</strong>{" "}
              {t("(Onaylı planı yeniden düzenlemek için")}{" "}
              <strong>Approved → Draft</strong> {t("geçişi kullanılır).")}{" "}
              {t("Yalnızca API'nin izin verdiği durum geçişleri gösterilir.")}
            </p>
          </div>
          <div className="filter-group">
            <label htmlFor="plan-project-filter">{t("Proje Filtresi:")}</label>
            <select
              id="plan-project-filter"
              value={filterProjectId}
              onChange={(e) => setFilterProjectId(e.target.value)}
            >
              <option value="all">{t("Tüm Projeler")}</option>
              {projects.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading && plans.length === 0 ? (
          <p className="hint">{t("Yükleniyor...")}</p>
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
                {t("Test Plan Detayı & Sürüm Geçmişi:")} #{activePlan.id} · {activePlan.title}
              </h2>
              <p className="section-desc">
                {t("Proje:")}{" "}
                <strong>
                  {projectNames.get(activePlan.project_id) ?? `#${activePlan.project_id}`}
                </strong>{" "}
                · {t("Hedef Sürüm:")}{" "}
                <strong>
                  {activePlan.release_id
                    ? (releaseLabels.get(activePlan.release_id) ?? `#${activePlan.release_id}`)
                    : t("Genel")}
                </strong>{" "}
                · {t("Plan Sürümü:")} <StatusBadge text={activePlan.version} /> ·{" "}
                {t("Durum:")} <StatusBadge text={activePlan.status} /> ·{" "}
                {t("Oluşturan:")} <strong>{activePlan.created_by}</strong> (
                {formatIsoTime(activePlan.created_at, lang)})
              </p>
            </div>

            <div className="row-actions">
              <button type="button" className="secondary-btn" onClick={() => void handleDownload(activePlan.id, "html")}>
            {t("Canlı HTML Görüntüle")}
          </button>
              <button type="button" className="secondary-btn" onClick={() => void handleDownload(activePlan.id, "pdf")}>
            {t("Canlı PDF İndir")}
          </button>
              {canTakeSnapshot && (
                <button
                  type="button"
                  disabled={creatingSnapshotId === activePlan.id}
                  onClick={() => void handleCreateSnapshot(activePlan)}
                >
                  {creatingSnapshotId === activePlan.id
                    ? t("Snapshot Alınıyor...")
                    : t("Anlık Görüntü (Snapshot) Kaydet")}
                </button>
              )}
            </div>
          </div>

          <div className="transition-box" style={{ marginBottom: 14 }}>
            <div className="inline-controls">
              <div>
                <h3>{t("İzin Verilen Durum Geçişleri (Draft → In Review → Approved)")}</h3>
                <p className="hint" style={{ marginTop: 2 }}>
                  {t("Doğrudan")} <code>Draft → Approved</code>{" "}
                  {t("geçişi yapılamaz; önce")} <code>In Review</code>{" "}
                  {t("durumuna geçirilmelidir.")}
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
                    {t("Taslağı Formda Düzenle")}
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">{t("1. Kapsam (Scope)")}</span>
              <p className="expected-text">{activePlan.scope || t("Belirtilmedi.")}</p>
            </div>
            <div className="detail-item">
              <span className="detail-label">{t("2. Test Yaklaşımı (Approach)")}</span>
              <p className="expected-text">{activePlan.approach || t("Belirtilmedi.")}</p>
            </div>
            <div className="detail-item">
              <span className="detail-label">
                {t("3. Kabul / Red Kriterleri (Pass/Fail Criteria)")}
              </span>
              <p className="expected-text">
                {activePlan.pass_fail_criteria || t("Belirtilmedi.")}
              </p>
            </div>
            <div className="detail-item">
              <span className="detail-label">
                {t("4. Test Ortamı ve Çıktılar (Environment)")}
              </span>
              <p className="expected-text">{activePlan.environment || t("Belirtilmedi.")}</p>
            </div>
            <div className="detail-item">
              <span className="detail-label">{t("5. Takvim ve Riskler (Schedule & Risks)")}</span>
              <p className="expected-text">{activePlan.schedule_risks || t("Belirtilmedi.")}</p>
            </div>
          </div>

          <h3>{t("Sürüm Geçmişi ve Anlık Görüntüler (Snapshots)")}</h3>
          <p className="section-desc">
            {t(
              "Her snapshot alındığı andaki Test Plan metnini, gereksinim izlenebilirliğini, test vakalarını, defect kayıtlarını ve metrik özetini değiştirilemez olarak saklar ve o sürüme ait HTML / PDF indirilmesini sağlar.",
            )}
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
                    {t("Snapshot #{id} Özeti", { id: previewSnapshot.id })} ·{" "}
                    {t("Sürüm")} {previewSnapshot.version} ({previewSnapshot.status})
                  </strong>
                  <p className="hint" style={{ marginTop: 2 }}>
                    {t("Üreten:")} {previewSnapshot.generated_by} ·{" "}
                    {formatIsoTime(previewSnapshot.generated_at, lang)}
                  </p>
                </div>
                <div className="row-actions">
                  <button type="button" className="secondary-btn" onClick={() => void handleDownload(activePlan.id, "html", previewSnapshot.id)}>
            {t("Tam HTML Raporu Aç")}
          </button>
                  <button type="button" className="secondary-btn" onClick={() => void handleDownload(activePlan.id, "pdf", previewSnapshot.id)}>
            {t("PDF İndir")}
          </button>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => setPreviewSnapshot(null)}
                  >
                    {t("Kapat")}
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
