import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  Defect,
  ExecutionStatus,
  formatErrorMessage,
  isEndpointUnavailableError,
  Project,
  RECORDABLE_EXECUTION_STATUSES,
  RecordableExecutionStatus,
  Release,
  SEVERITIES,
  TestCase,
  TestExecution,
  TestRun,
  TestSuite,
  User,
} from "../api";
import { DataTable, DataTableColumn } from "../components/DataTable";
import { ErrorAlert } from "../components/ErrorAlert";
import { FormField } from "../components/FormField";
import { StatusBadge } from "../components/StatusBadge";
import {
  attachDefectToPreviewExecution,
  createPreviewTestRun,
  loadPreviewTestRuns,
  loadPreviewTestSuites,
  mergeTestCasesWithPreview,
  recordPreviewExecution,
} from "../previewStore";
import {
  hasFormErrors,
  TestRunFormErrors,
  validateDefectForm,
  validateTestRunForm,
} from "../validation";

export type TestRunsPageProps = {
  user: User | null;
};

type ExecutionDraft = {
  status: RecordableExecutionStatus;
  actual_result: string;
  notes: string;
};

function summarizeRun(run: TestRun) {
  const counts: Record<ExecutionStatus, number> = {
    Passed: 0,
    Failed: 0,
    Blocked: 0,
    Skipped: 0,
    "Not Run": 0,
  };
  for (const ex of run.executions) {
    counts[ex.status] = (counts[ex.status] ?? 0) + 1;
  }
  const total = run.executions.length;
  const executed = total - counts["Not Run"];
  const passRate = executed > 0 ? Math.round((counts.Passed / executed) * 1000) / 10 : 0;
  return { counts, total, executed, passRate };
}

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

export function TestRunsPage({ user }: TestRunsPageProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [releases, setReleases] = useState<Release[]>([]);
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [rawServerCases, setRawServerCases] = useState<TestCase[]>([]);
  const [defects, setDefects] = useState<Defect[]>([]);
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [previewMode, setPreviewMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Create Run form state
  const [runName, setRunName] = useState("");
  const [runProjectId, setRunProjectId] = useState("");
  const [runReleaseId, setRunReleaseId] = useState("");
  const [runSuiteId, setRunSuiteId] = useState("");
  const [runCaseIds, setRunCaseIds] = useState<string[]>([]);
  const [runFormErrors, setRunFormErrors] = useState<TestRunFormErrors>({});

  // Execution row drafts & inline step preview
  const [drafts, setDrafts] = useState<Record<number, ExecutionDraft>>({});
  const [expandedExecId, setExpandedExecId] = useState<number | null>(null);
  const [savingExecId, setSavingExecId] = useState<number | null>(null);

  // Inline defect creation from failed execution
  const [defectExecId, setDefectExecId] = useState<number | null>(null);
  const [defectTitle, setDefectTitle] = useState("");
  const [defectSeverity, setDefectSeverity] = useState("High");
  const [defectError, setDefectError] = useState("");

  // History filters
  const [historyReleaseFilter, setHistoryReleaseFilter] = useState("all");
  const [historySearch, setHistorySearch] = useState("");

  const canExecute =
    user !== null &&
    (user.role === "Admin" || user.role === "Test Lead" || user.role === "Tester");

  const serverCaseIds = useMemo(
    () => new Set(rawServerCases.map((tc) => tc.id)),
    [rawServerCases],
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [projs, rels, cases, defs] = await Promise.all([
        api.projects(),
        api.releases(),
        api.testCases(),
        api.defects(),
      ]);

      let loadedSuites: TestSuite[];
      try {
        loadedSuites = await api.testSuites();
      } catch (err) {
        if (isEndpointUnavailableError(err)) {
          loadedSuites = loadPreviewTestSuites(projs);
        } else {
          throw err;
        }
      }

      const mergedCases = mergeTestCasesWithPreview(cases);
      let loadedRuns: TestRun[] = [];
      let isPreview = false;

      try {
        loadedRuns = await api.testRuns();
      } catch (err) {
        if (isEndpointUnavailableError(err)) {
          isPreview = true;
          loadedRuns = loadPreviewTestRuns(projs, rels, mergedCases, defs);
        } else {
          throw err;
        }
      }

      setProjects(projs);
      setReleases(rels);
      setSuites(loadedSuites);
      setRawServerCases(cases);
      setTestCases(mergedCases);
      setDefects(defs);
      setRuns(loadedRuns);
      setPreviewMode(isPreview);
      setRunProjectId((prev) => prev || (projs[0] ? String(projs[0].id) : ""));
      setSelectedRunId((prev) => {
        if (prev && loadedRuns.some((r) => r.id === prev)) return prev;
        return loadedRuns[0]?.id ?? null;
      });
      setError("");
    } catch (err) {
      setError(formatErrorMessage(err, "Test koşumları yüklenemedi."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData, user]);

  const activeRun = useMemo(
    () => runs.find((r) => r.id === selectedRunId) ?? null,
    [runs, selectedRunId],
  );

  useEffect(() => {
    if (!activeRun) return;
    const nextDrafts: Record<number, ExecutionDraft> = {};
    for (const ex of activeRun.executions) {
      nextDrafts[ex.id] = {
        status: ex.status === "Not Run" ? "Passed" : ex.status,
        actual_result: ex.actual_result,
        notes: ex.notes,
      };
    }
    setDrafts(nextDrafts);
  }, [activeRun]);

  const caseById = useMemo(
    () => new Map(testCases.map((tc) => [tc.id, tc])),
    [testCases],
  );

  const projectNames = useMemo(
    () => new Map(projects.map((p) => [p.id, p.name])),
    [projects],
  );

  const releaseLabels = useMemo(
    () => new Map(releases.map((r) => [r.id, r.version])),
    [releases],
  );

  const defectById = useMemo(
    () => new Map(defects.map((d) => [d.id, d])),
    [defects],
  );

  function handleSuiteTemplateChange(suiteIdStr: string) {
    setRunSuiteId(suiteIdStr);
    if (!suiteIdStr) return;
    const suite = suites.find((s) => String(s.id) === suiteIdStr);
    if (suite) {
      setRunCaseIds(suite.test_cases.filter((id) => caseById.has(id)));
      if (runFormErrors.testCaseIds) {
        setRunFormErrors((prev) => ({ ...prev, testCaseIds: undefined }));
      }
    }
  }

  async function handleCreateRun(e: FormEvent) {
    e.preventDefault();
    const validationErrors = validateTestRunForm({
      name: runName,
      projectId: runProjectId,
      testCaseIds: runCaseIds,
    });
    setRunFormErrors(validationErrors);
    if (hasFormErrors(validationErrors)) return;

    const payload = {
      name: runName.trim(),
      project_id: Number(runProjectId),
      release_id: runReleaseId ? Number(runReleaseId) : null,
      suite_id: runSuiteId ? Number(runSuiteId) : null,
      test_case_ids: runCaseIds,
    };

    setSaving(true);
    try {
      const created = await api.createTestRun(payload);
      setRunName("");
      setRunSuiteId("");
      setRunCaseIds([]);
      setRunFormErrors({});
      setSelectedRunId(created.id);
      setNotice(`"${created.name}" test koşumu başlatıldı.`);
      setError("");
      await loadData();
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        const created = createPreviewTestRun(
          payload,
          user?.username ?? "tester",
          projects,
          releases,
          testCases,
          defects,
        );
        setPreviewMode(true);
        setRunName("");
        setRunSuiteId("");
        setRunCaseIds([]);
        setRunFormErrors({});
        setSelectedRunId(created.id);
        setNotice(
          `PLN-17 uç noktası bekleniyor: "${created.name}" yerel önizleme koşumu olarak oluşturuldu.`,
        );
        setError("");
        await loadData();
      } else {
        setError(formatErrorMessage(err, "Test koşumu oluşturulamadı."));
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveExecution(ex: TestExecution) {
    if (!canExecute || !activeRun) return;
    const draft = drafts[ex.id];
    if (!draft) return;

    const payload = {
      status: draft.status,
      actual_result: draft.actual_result,
      notes: draft.notes,
    };

    setSavingExecId(ex.id);
    try {
      await api.recordExecution(activeRun.id, ex.id, payload);
      setNotice(`${ex.test_case_id} yürütme sonucu (${draft.status}) kaydedildi.`);
      setError("");
      await loadData();
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        recordPreviewExecution(activeRun.id, ex.id, payload, user?.username ?? "tester");
        setPreviewMode(true);
        setNotice(
          `${ex.test_case_id} yürütme sonucu (${draft.status}) yerel önizleme deposuna kaydedildi.`,
        );
        setError("");
        await loadData();
      } else {
        setError(formatErrorMessage(err, "Yürütme sonucu kaydedilemedi."));
      }
    } finally {
      setSavingExecId(null);
    }
  }

  function openDefectForm(ex: TestExecution) {
    const tc = caseById.get(ex.test_case_id);
    setDefectExecId(ex.id);
    setDefectTitle(
      `[${ex.test_case_id}] ${tc ? tc.title : "Test vakası"} yürütmesi başarısız`,
    );
    setDefectSeverity(tc?.priority === "Critical" ? "Critical" : "High");
    setDefectError("");
  }

  async function handleCreateDefectFromExecution(ex: TestExecution, e: FormEvent) {
    e.preventDefault();
    if (!activeRun || !canExecute) return;

    const validation = validateDefectForm({
      title: defectTitle,
      severity: defectSeverity,
      testCase: serverCaseIds.has(ex.test_case_id) ? ex.test_case_id : "",
    });
    if (validation.title || validation.severity) {
      setDefectError(validation.title ?? validation.severity ?? "Geçersiz defect bilgisi.");
      return;
    }

    setSavingExecId(ex.id);
    try {
      let created: Defect;
      try {
        created = await api.createDefectFromExecution(activeRun.id, ex.id, {
          title: defectTitle.trim(),
          severity: defectSeverity,
        });
      } catch (err) {
        if (isEndpointUnavailableError(err)) {
          // PLN-17 endpoint henüz yok; gerçek POST /api/defects uç noktasını kullan
          const linkedServerCase = serverCaseIds.has(ex.test_case_id) ? ex.test_case_id : null;
          created = await api.createDefect(defectTitle.trim(), defectSeverity, linkedServerCase);
          attachDefectToPreviewExecution(activeRun.id, ex.id, created.id);
        } else {
          throw err;
        }
      }

      setDefectExecId(null);
      setDefectTitle("");
      setDefectError("");
      setNotice(
        `Başarısız yürütmeden #${created.id} (${created.title}) defect kaydı oluşturuldu ve bağlandı.`,
      );
      setError("");
      await loadData();
    } catch (err) {
      setDefectError(formatErrorMessage(err, "Defect oluşturulamadı."));
    } finally {
      setSavingExecId(null);
    }
  }

  const filteredRuns = useMemo(() => {
    const q = historySearch.trim().toLowerCase();
    return runs.filter((run) => {
      if (historyReleaseFilter !== "all" && String(run.release_id ?? "") !== historyReleaseFilter) {
        return false;
      }
      if (q && !run.name.toLowerCase().includes(q) && !`#${run.id}`.includes(q)) {
        return false;
      }
      return true;
    });
  }, [runs, historyReleaseFilter, historySearch]);

  const activeSummary = useMemo(
    () => (activeRun ? summarizeRun(activeRun) : null),
    [activeRun],
  );

  const historyColumns: DataTableColumn<TestRun>[] = [
    { key: "id", header: "#", render: (r) => <strong>#{r.id}</strong> },
    { key: "name", header: "Koşum Adı", render: (r) => r.name },
    {
      key: "project_release",
      header: "Proje / Sürüm",
      render: (r) => {
        const proj = projectNames.get(r.project_id) ?? `#${r.project_id}`;
        const rel = r.release_id ? releaseLabels.get(r.release_id) : null;
        return rel ? `${proj} · ${rel}` : proj;
      },
    },
    { key: "created_by", header: "Başlatan", render: (r) => r.created_by },
    {
      key: "created_at",
      header: "Tarih",
      render: (r) => <span className="timeline-time">{formatIsoTime(r.created_at)}</span>,
    },
    {
      key: "breakdown",
      header: "Sonuç Dağılımı",
      render: (r) => {
        const s = summarizeRun(r);
        return (
          <div className="badge-list">
            <span className="badge passed">P: {s.counts.Passed}</span>
            <span className="badge failed">F: {s.counts.Failed}</span>
            <span className="badge blocked">B: {s.counts.Blocked}</span>
            <span className="badge skipped">S: {s.counts.Skipped}</span>
            <span className="badge not-run">NR: {s.counts["Not Run"]}</span>
          </div>
        );
      },
    },
    {
      key: "pass_rate",
      header: "Başarı",
      render: (r) => <strong>{summarizeRun(r).passRate}%</strong>,
    },
    {
      key: "action",
      header: "İşlem",
      render: (r) => (
        <button
          type="button"
          className={r.id === selectedRunId ? "secondary-btn" : ""}
          onClick={() => setSelectedRunId(r.id)}
        >
          {r.id === selectedRunId ? "Seçili" : "Yürüt / İncele"}
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
          <button type="button" className="secondary-btn" onClick={() => setNotice("")}>
            Kapat
          </button>
        </section>
      )}

      {previewMode && (
        <section className="info-banner" role="note">
          <div>
            <strong>Önizleme Modu (PLN-17 Backend Bekleniyor):</strong>{" "}
            Test koşumu ve yürütme kayıtları PLN-17 uç noktaları (<code>/api/test-runs</code>)
            birleşene kadar yerel tarayıcı deposunda çalışır. Başarısız yürütmeden açtığınız
            defect kayıtları ise doğrudan gerçek <code>POST /api/defects</code> API&apos;sine
            yazılır ve veritabanında kalıcı olur.
          </div>
        </section>
      )}

      {!user && (
        <section className="role-notice">
          <span>
            Test koşumu başlatmak, sonuç girmek veya başarısız yürütmeden defect açmak için{" "}
            <Link to="/login">giriş yapın</Link>.
          </span>
        </section>
      )}

      {user && !canExecute && (
        <section className="role-notice">
          <span>
            Aktif rol: <StatusBadge text={user.role} /> · Test koşumu yürütme işlemleri yalnızca{" "}
            <strong>Admin</strong>, <strong>Test Lead</strong> ve <strong>Tester</strong>{" "}
            rolleri içindir.
          </span>
        </section>
      )}

      {canExecute && (
        <section>
          <h2>Yeni Test Koşumu Başlat</h2>
          <p className="section-desc">
            ISO/IEC/IEEE 29119-2 · Test Yürütme ve Test Olay Raporlama (R2, R4)
          </p>
          <form onSubmit={handleCreateRun} noValidate className="stacked-form">
            <div className="form-grid">
              <FormField id="run-name" label="Koşum Adı" required error={runFormErrors.name}>
                <input
                  id="run-name"
                  value={runName}
                  onChange={(e) => {
                    setRunName(e.target.value);
                    if (runFormErrors.name) {
                      setRunFormErrors((prev) => ({ ...prev, name: undefined }));
                    }
                  }}
                  placeholder="Örn: v1.0 Çıkış Öncesi Regresyon"
                />
              </FormField>

              <FormField
                id="run-project"
                label="Proje"
                required
                error={runFormErrors.projectId}
              >
                <select
                  id="run-project"
                  value={runProjectId}
                  onChange={(e) => setRunProjectId(e.target.value)}
                >
                  <option value="">Proje seçin</option>
                  {projects.map((p) => (
                    <option key={p.id} value={String(p.id)}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </FormField>

              <FormField id="run-release" label="Hedef Sürüm">
                <select
                  id="run-release"
                  value={runReleaseId}
                  onChange={(e) => setRunReleaseId(e.target.value)}
                >
                  <option value="">Sürüm seçilmedi</option>
                  {releases
                    .filter((r) => !runProjectId || String(r.project_id) === runProjectId)
                    .map((r) => (
                      <option key={r.id} value={String(r.id)}>
                        {r.version}
                      </option>
                    ))}
                </select>
              </FormField>

              <FormField id="run-suite" label="Suite Şablonu (Opsiyonel)">
                <select
                  id="run-suite"
                  value={runSuiteId}
                  onChange={(e) => handleSuiteTemplateChange(e.target.value)}
                >
                  <option value="">Elle test vakası seç</option>
                  {suites.map((s) => (
                    <option key={s.id} value={String(s.id)}>
                      {s.name} ({s.test_cases.length} vaka)
                    </option>
                  ))}
                </select>
              </FormField>
            </div>

            <div className="trace-panel">
              <div className="trace-panel-header">
                <strong>
                  Koşuma Alınacak Test Vakaları <span className="required-mark">*</span>
                </strong>
                {runFormErrors.testCaseIds && (
                  <span className="field-error" role="alert">
                    {runFormErrors.testCaseIds}
                  </span>
                )}
              </div>
              <div className="trace-checkbox-grid">
                {testCases.map((tc) => {
                  const checked = runCaseIds.includes(tc.id);
                  return (
                    <label key={tc.id} className="trace-checkbox-item">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          setRunCaseIds((prev) =>
                            e.target.checked
                              ? [...prev, tc.id]
                              : prev.filter((id) => id !== tc.id),
                          );
                          if (runFormErrors.testCaseIds) {
                            setRunFormErrors((prev) => ({ ...prev, testCaseIds: undefined }));
                          }
                        }}
                      />
                      <span>
                        <strong>{tc.stable_key ?? tc.id}</strong> · {tc.title}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div className="row-actions">
              <button type="submit" disabled={saving}>
                Test Koşumu Başlat
              </button>
              <button
                type="button"
                className="secondary-btn"
                onClick={() => setRunCaseIds(testCases.map((tc) => tc.id))}
              >
                Tümünü Seç
              </button>
            </div>
          </form>
        </section>
      )}

      {activeRun && activeSummary && (
        <section>
          <div className="section-header">
            <div>
              <h2>
                Aktif Koşum: #{activeRun.id} · {activeRun.name}
              </h2>
              <p className="section-desc">
                {projectNames.get(activeRun.project_id) ?? `Proje #${activeRun.project_id}`}
                {activeRun.release_id
                  ? ` · Sürüm ${releaseLabels.get(activeRun.release_id) ?? activeRun.release_id}`
                  : ""}
                {" · "}Başlatan: <strong>{activeRun.created_by}</strong> (
                {formatIsoTime(activeRun.created_at)})
              </p>
            </div>
            <div className="badge-list">
              <span className="badge passed">Passed: {activeSummary.counts.Passed}</span>
              <span className="badge failed">Failed: {activeSummary.counts.Failed}</span>
              <span className="badge blocked">Blocked: {activeSummary.counts.Blocked}</span>
              <span className="badge skipped">Skipped: {activeSummary.counts.Skipped}</span>
              <span className="badge not-run">Not Run: {activeSummary.counts["Not Run"]}</span>
              <span className="badge">Başarı: {activeSummary.passRate}%</span>
              {!previewMode && (
                <>
                  <a
                    href={api.exportTestLogUrl(activeRun.id, "html")}
                    target="_blank"
                    rel="noreferrer"
                    className="detail-link"
                  >
                    Test Log (HTML)
                  </a>
                  <a
                    href={api.exportTestLogUrl(activeRun.id, "pdf")}
                    className="detail-link"
                  >
                    Test Log (PDF)
                  </a>
                </>
              )}
            </div>
          </div>

          {activeSummary.total > 0 && (
            <div
              className="run-progress-bar"
              role="img"
              aria-label={`Koşum ilerleme çubuğu: ${activeSummary.executed}/${activeSummary.total} yürütüldü`}
            >
              {(
                [
                  ["passed", activeSummary.counts.Passed],
                  ["failed", activeSummary.counts.Failed],
                  ["blocked", activeSummary.counts.Blocked],
                  ["skipped", activeSummary.counts.Skipped],
                  ["not-run", activeSummary.counts["Not Run"]],
                ] as const
              ).map(([cls, count]) =>
                count > 0 ? (
                  <div
                    key={cls}
                    className={`run-progress-seg ${cls}`}
                    style={{ width: `${(count / activeSummary.total) * 100}%` }}
                    title={`${cls}: ${count}`}
                  />
                ) : null,
              )}
            </div>
          )}

          <div className="execution-list">
            {activeRun.executions.map((ex) => {
              const tc = caseById.get(ex.test_case_id);
              const draft = drafts[ex.id] ?? {
                status: ex.status === "Not Run" ? "Passed" : ex.status,
                actual_result: ex.actual_result,
                notes: ex.notes,
              };
              const relatedResolvedDefects = defects.filter(
                (d) => d.test_case === ex.test_case_id && d.status === "Resolved",
              );
              const isExpanded = expandedExecId === ex.id;
              const isOpeningDefect = defectExecId === ex.id;

              return (
                <article key={ex.id} className="execution-card">
                  <div className="execution-card-header">
                    <div>
                      <strong>{ex.test_case_id}</strong> ·{" "}
                      <span>{tc?.title ?? "Test vakası"}</span>
                      <div className="badge-list" style={{ marginTop: 4 }}>
                        <StatusBadge text={ex.status} />
                        {ex.executed_by && (
                          <span className="hint">
                            Son yürüten: {ex.executed_by} ({formatIsoTime(ex.executed_at)})
                          </span>
                        )}
                        {ex.defect_ids.map((defId) => {
                          const defObj = defectById.get(defId);
                          return (
                            <Link key={defId} to={`/defects/${defId}`} className="detail-link">
                              Defect #{defId}
                              {defObj ? ` (${defObj.status})` : ""}
                            </Link>
                          );
                        })}
                      </div>
                    </div>

                    <div className="row-actions">
                      <button
                        type="button"
                        className="secondary-btn"
                        onClick={() => setExpandedExecId(isExpanded ? null : ex.id)}
                      >
                        {isExpanded ? "Adımları Gizle" : "Adımlar & Beklenen"}
                      </button>
                      {canExecute && ex.status === "Failed" && (
                        <button
                          type="button"
                          className="danger-btn"
                          onClick={() =>
                            isOpeningDefect ? setDefectExecId(null) : openDefectForm(ex)
                          }
                        >
                          {isOpeningDefect ? "Vazgeç" : "Başarısız Yürütmeden Defect Aç"}
                        </button>
                      )}
                    </div>
                  </div>

                  {relatedResolvedDefects.length > 0 && (
                    <p className="hint" style={{ margin: "6px 0" }}>
                      Doğrulama Notu (R4): İlişkili{" "}
                      {relatedResolvedDefects.map((d) => `#${d.id}`).join(", ")} defect
                      kayıtları <strong>Resolved</strong> durumda. Burada{" "}
                      <strong>Passed</strong> yürütmesi kaydetmek doğrulama kanıtı oluşturur.
                    </p>
                  )}

                  {isExpanded && tc && (
                    <div className="case-detail-drawer" style={{ marginTop: 8, marginBottom: 10 }}>
                      <div className="detail-grid" style={{ marginBottom: 0 }}>
                        <div className="detail-item">
                          <span className="detail-label">Test Adımları</span>
                          <ol className="steps-list">
                            {(tc.steps ?? ["Adım tanımlanmamış."]).map((step, i) => (
                              <li key={i}>{step}</li>
                            ))}
                          </ol>
                        </div>
                        <div className="detail-item">
                          <span className="detail-label">Beklenen Sonuç</span>
                          <p className="expected-text">{tc.expected_result ?? "—"}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {canExecute && (
                    <div className="execution-controls">
                      <div className="form-field">
                        <label htmlFor={`exec-status-${ex.id}`}>Sonuç</label>
                        <select
                          id={`exec-status-${ex.id}`}
                          value={draft.status}
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [ex.id]: {
                                ...draft,
                                status: e.target.value as RecordableExecutionStatus,
                              },
                            }))
                          }
                        >
                          {RECORDABLE_EXECUTION_STATUSES.map((s) => (
                            <option key={s} value={s}>
                              {s}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="form-field" style={{ flex: 2 }}>
                        <label htmlFor={`exec-actual-${ex.id}`}>Gerçekleşen Sonuç</label>
                        <input
                          id={`exec-actual-${ex.id}`}
                          value={draft.actual_result}
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [ex.id]: { ...draft, actual_result: e.target.value },
                            }))
                          }
                          placeholder="Gözlemlenen davranış / çıktı"
                        />
                      </div>

                      <div className="form-field" style={{ flex: 1 }}>
                        <label htmlFor={`exec-notes-${ex.id}`}>Not</label>
                        <input
                          id={`exec-notes-${ex.id}`}
                          value={draft.notes}
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [ex.id]: { ...draft, notes: e.target.value },
                            }))
                          }
                          placeholder="Ortam veya kısa not"
                        />
                      </div>

                      <div className="form-actions">
                        <button
                          type="button"
                          disabled={savingExecId === ex.id}
                          onClick={() => void handleSaveExecution(ex)}
                        >
                          {savingExecId === ex.id ? "Kaydediliyor..." : "Sonucu Kaydet"}
                        </button>
                      </div>
                    </div>
                  )}

                  {isOpeningDefect && canExecute && (
                    <form
                      className="inline-defect-drawer"
                      onSubmit={(e) => void handleCreateDefectFromExecution(ex, e)}
                      noValidate
                    >
                      <strong>Başarısız Yürütmeden Yeni Defect Aç ({ex.test_case_id})</strong>
                      {defectError && (
                        <span className="field-error" role="alert">
                          {defectError}
                        </span>
                      )}
                      <div className="form-grid">
                        <FormField id={`def-title-${ex.id}`} label="Defect Başlığı" required>
                          <input
                            id={`def-title-${ex.id}`}
                            value={defectTitle}
                            onChange={(e) => setDefectTitle(e.target.value)}
                          />
                        </FormField>
                        <FormField id={`def-sev-${ex.id}`} label="Önem Derecesi" required>
                          <select
                            id={`def-sev-${ex.id}`}
                            value={defectSeverity}
                            onChange={(e) => setDefectSeverity(e.target.value)}
                          >
                            {SEVERITIES.map((s) => (
                              <option key={s} value={s}>
                                {s}
                              </option>
                            ))}
                          </select>
                        </FormField>
                      </div>
                      <div className="row-actions">
                        <button type="submit" disabled={savingExecId === ex.id}>
                          Defect Oluştur &amp; Bağla
                        </button>
                        <button
                          type="button"
                          className="secondary-btn"
                          onClick={() => setDefectExecId(null)}
                        >
                          İptal
                        </button>
                      </div>
                    </form>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <div className="section-header">
          <div>
            <h2>Test Koşum Geçmişi</h2>
            <p className="section-desc">
              Önceki ve aktif test koşumlarını sürüm veya ada göre filtreleyip inceleyin.
            </p>
          </div>
          <div className="filter-group">
            <input
              aria-label="Koşum geçmişinde ara"
              placeholder="Koşum adı veya #ID ara..."
              value={historySearch}
              onChange={(e) => setHistorySearch(e.target.value)}
            />
            <select
              aria-label="Sürüme göre filtrele"
              value={historyReleaseFilter}
              onChange={(e) => setHistoryReleaseFilter(e.target.value)}
            >
              <option value="all">Tüm Sürümler</option>
              {releases.map((r) => (
                <option key={r.id} value={String(r.id)}>
                  {r.version}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading ? (
          <p className="hint">Yükleniyor...</p>
        ) : (
          <DataTable
            columns={historyColumns}
            rows={filteredRuns}
            getRowKey={(r) => r.id}
            emptyMessage="Kayıtlı test koşumu bulunamadı."
            ariaLabel="Test Koşum Geçmişi"
          />
        )}
      </section>
    </>
  );
}
