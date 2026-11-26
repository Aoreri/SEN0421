import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  formatErrorMessage,
  isEndpointUnavailableError,
  Project,
  Requirement,
  TEST_PRIORITIES,
  TestCase,
  TestPriority,
  TestSuite,
  User,
} from "../api";
import { DataTable, DataTableColumn } from "../components/DataTable";
import { ErrorAlert } from "../components/ErrorAlert";
import { FormField } from "../components/FormField";
import { StatusBadge } from "../components/StatusBadge";
import {
  deletePreviewTestCase,
  deletePreviewTestSuite,
  loadPreviewTestSuites,
  mergeTestCasesWithPreview,
  savePreviewTestCase,
  savePreviewTestSuite,
  togglePreviewRequirementLink,
} from "../previewStore";
import {
  hasFormErrors,
  TestCaseFormErrors,
  TestSuiteFormErrors,
  validateTestCaseForm,
  validateTestSuiteForm,
} from "../validation";
import { useT } from "../i18n";

type ActiveTab = "cases" | "suites" | "matrix";

export type TestCasesPageProps = {
  user: User | null;
};

export function TestCasesPage({ user }: TestCasesPageProps) {
  const t = useT();
  const [activeTab, setActiveTab] = useState<ActiveTab>("cases");
  const [projects, setProjects] = useState<Project[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [rawServerCases, setRawServerCases] = useState<TestCase[]>([]);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [previewMode, setPreviewMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Test case filters
  const [searchQuery, setSearchQuery] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [automationFilter, setAutomationFilter] = useState<string>("all");
  const [suiteFilter, setSuiteFilter] = useState<string>("all");
  const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);

  // Test case form state
  const [editingCaseId, setEditingCaseId] = useState<string | null>(null);
  const [stableKey, setStableKey] = useState("");
  const [caseTitle, setCaseTitle] = useState("");
  const [casePriority, setCasePriority] = useState<TestPriority>("Medium");
  const [isAutomated, setIsAutomated] = useState(false);
  const [caseSuiteId, setCaseSuiteId] = useState("");
  const [stepsText, setStepsText] = useState("");
  const [expectedResult, setExpectedResult] = useState("");
  const [caseRequirements, setCaseRequirements] = useState<string[]>([]);
  const [caseFormErrors, setCaseFormErrors] = useState<TestCaseFormErrors>({});

  // Test suite form state
  const [editingSuiteId, setEditingSuiteId] = useState<number | null>(null);
  const [suiteProjectId, setSuiteProjectId] = useState("");
  const [suiteName, setSuiteName] = useState("");
  const [suiteDescription, setSuiteDescription] = useState("");
  const [suiteCaseIds, setSuiteCaseIds] = useState<string[]>([]);
  const [suiteFormErrors, setSuiteFormErrors] = useState<TestSuiteFormErrors>({});

  // Matrix filter
  const [matrixProjectFilter, setMatrixProjectFilter] = useState<string>("all");
  const [matrixSavingCell, setMatrixSavingCell] = useState<string | null>(null);

  const canManage =
    user !== null &&
    (user.role === "Admin" || user.role === "Test Lead" || user.role === "Tester");

  const serverCaseIds = useMemo(
    () => new Set(rawServerCases.map((tc) => tc.id)),
    [rawServerCases],
  );

  const loadData = useCallback(async () => {
    if (!user) {
      setProjects([]);
      setRequirements([]);
      setRawServerCases([]);
      setTestCases([]);
      setSuites([]);
      setError("");
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [projs, reqs, cases] = await Promise.all([
        api.projects(),
        api.requirements(),
        api.testCases(),
      ]);

      let loadedSuites: TestSuite[] = [];
      let isPreview = false;

      try {
        loadedSuites = await api.testSuites();
      } catch (err) {
        if (isEndpointUnavailableError(err)) {
          isPreview = true;
          loadedSuites = loadPreviewTestSuites(projs);
        } else {
          throw err;
        }
      }

      const mergedCases = isPreview ? mergeTestCasesWithPreview(cases) : cases;
      const mergedWithReqLinks = mergedCases.map((tc) => {
        const linkedFromReqs = reqs
          .filter((r) => r.test_cases.includes(tc.id))
          .map((r) => r.id);
        const combined = Array.from(new Set([...(tc.requirements ?? []), ...linkedFromReqs]));
        return {
          ...tc,
          requirements: combined,
          requirement: combined[0] ?? tc.requirement ?? "",
        };
      });

      setProjects(projs);
      setRequirements(reqs);
      setRawServerCases(cases);
      setTestCases(mergedWithReqLinks);
      setSuites(loadedSuites);
      setPreviewMode(isPreview);
      setSuiteProjectId((prev) => prev || (projs[0] ? String(projs[0].id) : ""));
      setError("");
    } catch (err) {
      setError(
        formatErrorMessage(err, t("Test vakaları ve izlenebilirlik verileri yüklenemedi.")),
      );
    } finally {
      setLoading(false);
    }
  }, [user, t]);

  useEffect(() => {
    void loadData();
  }, [loadData, user]);

  function resetCaseForm() {
    setEditingCaseId(null);
    setStableKey("");
    setCaseTitle("");
    setCasePriority("Medium");
    setIsAutomated(false);
    setCaseSuiteId("");
    setStepsText("");
    setExpectedResult("");
    setCaseRequirements([]);
    setCaseFormErrors({});
  }

  function startEditCase(tc: TestCase) {
    setEditingCaseId(tc.id);
    setStableKey(tc.stable_key ?? tc.id);
    setCaseTitle(tc.title);
    setCasePriority(tc.priority ?? "Medium");
    setIsAutomated(Boolean(tc.automated));
    setCaseSuiteId(tc.suite_id ? String(tc.suite_id) : "");
    setStepsText((tc.steps ?? []).join("\n"));
    setExpectedResult(tc.expected_result ?? "");
    setCaseRequirements(
      tc.requirements.length > 0 ? tc.requirements : tc.requirement ? [tc.requirement] : [],
    );
    setCaseFormErrors({});
    setActiveTab("cases");
  }

  async function handleCaseSubmit(e: FormEvent) {
    e.preventDefault();
    const validationErrors = validateTestCaseForm({
      stableKey,
      title: caseTitle,
      priority: casePriority,
      stepsText,
      expectedResult,
      requirements: caseRequirements,
    });
    setCaseFormErrors(validationErrors);
    if (hasFormErrors(validationErrors)) return;

    const steps = stepsText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    const payload = {
      id: (editingCaseId ?? stableKey).trim(),
      title: caseTitle.trim(),
      priority: casePriority,
      automated: isAutomated,
      steps,
      expected_result: expectedResult.trim(),
      requirements: caseRequirements,
      suite_id: caseSuiteId ? Number(caseSuiteId) : null,
    };

    setSaving(true);
    try {
      if (editingCaseId) {
        await api.updateTestCase(editingCaseId, payload);
      } else {
        await api.createTestCase(payload);
      }
      resetCaseForm();
      setNotice(t("Test vakası kaydedildi."));
      setError("");
      await loadData();
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        savePreviewTestCase(payload, editingCaseId, serverCaseIds);
        setPreviewMode(true);
        resetCaseForm();
        setNotice(
          t("Değişiklik şimdilik yalnızca bu tarayıcıda (önizleme) kaydedildi."),
        );
        setError("");
        await loadData();
      } else {
        setError(formatErrorMessage(err, t("Test vakası kaydedilemedi.")));
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteCase(tc: TestCase) {
    setSaving(true);
    try {
      await api.deleteTestCase(tc.id);
      if (editingCaseId === tc.id) resetCaseForm();
      if (expandedCaseId === tc.id) setExpandedCaseId(null);
      setNotice(t("{key} silindi.", { key: tc.stable_key ?? tc.id }));
      setError("");
      await loadData();
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        deletePreviewTestCase(tc.id);
        setPreviewMode(true);
        if (editingCaseId === tc.id) resetCaseForm();
        if (expandedCaseId === tc.id) setExpandedCaseId(null);
        setNotice(
          t("{key} yerel önizleme deposundan kaldırıldı.", { key: tc.stable_key ?? tc.id }),
        );
        setError("");
        await loadData();
      } else {
        setError(formatErrorMessage(err, t("Test vakası silinemedi.")));
      }
    } finally {
      setSaving(false);
    }
  }

  function resetSuiteForm() {
    setEditingSuiteId(null);
    setSuiteName("");
    setSuiteDescription("");
    setSuiteCaseIds([]);
    setSuiteFormErrors({});
  }

  function startEditSuite(suite: TestSuite) {
    setEditingSuiteId(suite.id);
    setSuiteProjectId(String(suite.project_id));
    setSuiteName(suite.name);
    setSuiteDescription(suite.description);
    setSuiteCaseIds(suite.test_cases);
    setSuiteFormErrors({});
    setActiveTab("suites");
  }

  async function handleSuiteSubmit(e: FormEvent) {
    e.preventDefault();
    const validationErrors = validateTestSuiteForm({
      projectId: suiteProjectId,
      name: suiteName,
      description: suiteDescription,
    });
    setSuiteFormErrors(validationErrors);
    if (hasFormErrors(validationErrors)) return;

    const payload = {
      project_id: Number(suiteProjectId),
      name: suiteName.trim(),
      description: suiteDescription.trim(),
      test_cases: suiteCaseIds,
    };

    setSaving(true);
    try {
      let savedSuite: TestSuite;
      if (editingSuiteId !== null) {
        savedSuite = await api.updateTestSuite(
          editingSuiteId,
          payload.project_id,
          payload.name,
          payload.description,
        );
      } else {
        savedSuite = await api.createTestSuite(
          payload.project_id,
          payload.name,
          payload.description,
        );
      }
      const selectedSet = new Set(suiteCaseIds);
      for (const tc of testCases) {
        const shouldBeInSuite = selectedSet.has(tc.id);
        const currentlyInSuite = tc.suite_id === savedSuite.id;
        if (shouldBeInSuite && !currentlyInSuite && serverCaseIds.has(tc.id)) {
          await api.updateTestCase(tc.id, {
            title: tc.title,
            suite_id: savedSuite.id,
            priority: tc.priority,
            automated: tc.automated,
            steps: tc.steps,
            expected_result: tc.expected_result,
            status: tc.status as "Not Run" | "Passed" | "Failed" | "Blocked" | "Skipped",
            requirements: tc.requirements,
          });
        } else if (!shouldBeInSuite && currentlyInSuite && serverCaseIds.has(tc.id)) {
          await api.updateTestCase(tc.id, {
            title: tc.title,
            suite_id: null,
            priority: tc.priority,
            automated: tc.automated,
            steps: tc.steps,
            expected_result: tc.expected_result,
            status: tc.status as "Not Run" | "Passed" | "Failed" | "Blocked" | "Skipped",
            requirements: tc.requirements,
          });
        }
      }
      resetSuiteForm();
      setNotice(t("Test suite kaydedildi."));
      setError("");
      await loadData();
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        savePreviewTestSuite(payload, editingSuiteId, projects);
        setPreviewMode(true);
        resetSuiteForm();
        setNotice(
          t("Suite şimdilik yalnızca bu tarayıcıda (önizleme) kaydedildi."),
        );
        setError("");
        await loadData();
      } else {
        setError(formatErrorMessage(err, t("Test suite kaydedilemedi.")));
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteSuite(suite: TestSuite) {
    setSaving(true);
    try {
      await api.deleteTestSuite(suite.id);
      if (editingSuiteId === suite.id) resetSuiteForm();
      setNotice(t("{name} silindi.", { name: suite.name }));
      setError("");
      await loadData();
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        deletePreviewTestSuite(suite.id, projects);
        setPreviewMode(true);
        if (editingSuiteId === suite.id) resetSuiteForm();
        setNotice(t("{name} yerel önizleme deposundan silindi.", { name: suite.name }));
        setError("");
        await loadData();
      } else {
        setError(formatErrorMessage(err, t("Test suite silinemedi.")));
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleMatrixToggle(req: Requirement, tc: TestCase, willBeLinked: boolean) {
    if (!canManage) return;
    const currentlyLinked = !willBeLinked;

    if (currentlyLinked && tc.requirements.length <= 1) {
      setError(
        t("FR-REQ-01 gereği {key} en az bir gereksinime bağlı kalmalıdır.", {
          key: tc.stable_key ?? tc.id,
        }),
      );
      return;
    }

    const cellKey = `${req.id}::${tc.id}`;
    setMatrixSavingCell(cellKey);
    try {
      if (serverCaseIds.has(tc.id)) {
        const nextLinkedForReq = willBeLinked
          ? Array.from(new Set([...req.test_cases, tc.id]))
          : req.test_cases.filter((id) => id !== tc.id);
        await api.setRequirementTestCases(req.id, nextLinkedForReq);
      }
      if (previewMode || !serverCaseIds.has(tc.id)) {
        togglePreviewRequirementLink(req.id, tc.id, willBeLinked);
      }
      setError("");
      await loadData();
    } catch (err) {
      setError(formatErrorMessage(err, t("İzlenebilirlik bağlantısı güncellenemedi.")));
    } finally {
      setMatrixSavingCell(null);
    }
  }

  const projectNames = useMemo(
    () => new Map(projects.map((p) => [p.id, p.name])),
    [projects],
  );

  const suiteNames = useMemo(
    () => new Map(suites.map((s) => [s.id, s.name])),
    [suites],
  );

  const filteredCases = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return testCases.filter((tc) => {
      if (q) {
        const key = (tc.stable_key ?? tc.id).toLowerCase();
        const titleMatch = tc.title.toLowerCase().includes(q);
        const keyMatch = key.includes(q);
        if (!titleMatch && !keyMatch) return false;
      }
      if (priorityFilter !== "all" && (tc.priority ?? "Medium") !== priorityFilter) {
        return false;
      }
      if (automationFilter === "auto" && !tc.automated) return false;
      if (automationFilter === "manual" && tc.automated) return false;
      if (suiteFilter !== "all") {
        const suiteObj = suites.find((s) => String(s.id) === suiteFilter);
        const inSuite =
          String(tc.suite_id ?? "") === suiteFilter ||
          Boolean(suiteObj?.test_cases.includes(tc.id));
        if (!inSuite) return false;
      }
      return true;
    });
  }, [testCases, searchQuery, priorityFilter, automationFilter, suiteFilter, suites]);

  const filteredRequirements = useMemo(() => {
    if (matrixProjectFilter === "all") return requirements;
    return requirements.filter((r) => String(r.project_id) === matrixProjectFilter);
  }, [requirements, matrixProjectFilter]);

  const matrixStats = useMemo(() => {
    const totalReqs = filteredRequirements.length;
    const coveredReqs = filteredRequirements.filter((req) =>
      testCases.some((tc) => tc.requirements.includes(req.id)),
    );
    const uncoveredReqs = filteredRequirements.filter(
      (req) => !testCases.some((tc) => tc.requirements.includes(req.id)),
    );
    const totalLinks = filteredRequirements.reduce(
      (sum, req) => sum + testCases.filter((tc) => tc.requirements.includes(req.id)).length,
      0,
    );
    const coverageRate =
      totalReqs > 0 ? Math.round((coveredReqs.length / totalReqs) * 1000) / 10 : 0;

    return { totalReqs, coveredCount: coveredReqs.length, uncoveredReqs, totalLinks, coverageRate };
  }, [filteredRequirements, testCases]);

  const expandedCase = useMemo(
    () => testCases.find((tc) => tc.id === expandedCaseId) ?? null,
    [testCases, expandedCaseId],
  );

  const testCaseColumns: DataTableColumn<TestCase>[] = [
    {
      key: "stable_key",
      header: t("Anahtar"),
      render: (tc) => <code>{tc.stable_key ?? tc.id}</code>,
    },
    { key: "title", header: t("Başlık"), render: (tc) => tc.title },
    {
      key: "priority",
      header: t("Öncelik"),
      render: (tc) => <StatusBadge text={tc.priority ?? "Medium"} />,
    },
    {
      key: "automation",
      header: t("Otomasyon"),
      render: (tc) => (
        <span className={`badge ${tc.automated ? "auto-yes" : "auto-no"}`}>
          {tc.automated ? t("Otomatik") : t("Manuel")}
        </span>
      ),
    },
    {
      key: "suite",
      header: t("Suite"),
      render: (tc) => {
        const matchedSuite =
          (tc.suite_id ? suiteNames.get(tc.suite_id) : undefined) ??
          suites.find((s) => s.test_cases.includes(tc.id))?.name;
        return matchedSuite ?? <span className="hint">—</span>;
      },
    },
    {
      key: "requirements",
      header: t("Gereksinimler"),
      render: (tc) =>
        tc.requirements.length > 0 ? (
          <div className="badge-list">
            {tc.requirements.map((r) => (
              <span className="badge" key={r}>
                {r}
              </span>
            ))}
          </div>
        ) : (
          <span className="hint">—</span>
        ),
    },
    {
      key: "status",
      header: t("Son Durum"),
      render: (tc) => <StatusBadge text={tc.status} />,
    },
    {
      key: "actions",
      header: t("İşlemler"),
      render: (tc) => (
        <div className="row-actions">
          <button
            type="button"
            className="secondary-btn"
            onClick={() => setExpandedCaseId((prev) => (prev === tc.id ? null : tc.id))}
          >
            {expandedCaseId === tc.id ? t("Gizle") : t("Adımlar")}
          </button>
          {canManage && (
            <>
              <button
                type="button"
                className="secondary-btn"
                onClick={() => startEditCase(tc)}
              >
                {t("Düzenle")}
              </button>
              <button
                type="button"
                className="danger-btn"
                disabled={saving}
                onClick={() => void handleDeleteCase(tc)}
              >
                {t("Sil")}
              </button>
            </>
          )}
        </div>
      ),
    },
  ];

  const suiteColumns: DataTableColumn<TestSuite>[] = [
    { key: "name", header: t("Suite Adı"), render: (s) => <strong>{s.name}</strong> },
    {
      key: "project",
      header: t("Proje"),
      render: (s) => projectNames.get(s.project_id) ?? `#${s.project_id}`,
    },
    {
      key: "description",
      header: t("Açıklama"),
      render: (s) => s.description || <span className="hint">—</span>,
    },
    {
      key: "cases",
      header: t("Test Vakaları"),
      render: (s) =>
        s.test_cases.length > 0 ? (
          <div className="badge-list">
            {s.test_cases.map((id) => (
              <span className="badge" key={id}>
                {id}
              </span>
            ))}
          </div>
        ) : (
          <span className="hint">{t("Vaka atanmadı")}</span>
        ),
    },
    {
      key: "actions",
      header: t("İşlemler"),
      render: (s) =>
        canManage ? (
          <div className="row-actions">
            <button
              type="button"
              className="secondary-btn"
              onClick={() => startEditSuite(s)}
            >
              {t("Düzenle")}
            </button>
            <button
              type="button"
              className="danger-btn"
              disabled={saving}
              onClick={() => void handleDeleteSuite(s)}
            >
              {t("Sil")}
            </button>
          </div>
        ) : (
          <span className="hint">{t("Salt okunur")}</span>
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
            {t("Kapat")}
          </button>
        </section>
      )}

      {previewMode && (
        <section className="info-banner" role="note">
          <div>
            <strong>{t("Önizleme Modu:")}</strong>{" "}
            {t(
              "Gereksinimler ve mevcut test vakaları canlı okunur; mevcut test vakalarının matris değişiklikleri kalıcı olarak kaydedilir. Yeni test vakaları, adım/öncelik/otomasyon alanları ve test suite işlemleri şimdilik yalnızca bu tarayıcıda saklanır.",
            )}
          </div>
        </section>
      )}

      {!user && (
        <section className="role-notice">
          <span>
            {t("Test vakası, suite ve izlenebilirlik matrisi düzenleme işlemleri için")}{" "}
            <Link to="/login">{t("giriş yapın")}</Link>.
          </span>
        </section>
      )}

      {user && !canManage && (
        <section className="role-notice">
          <span>
            {t("Aktif rol:")} <StatusBadge text={user.role} /> ·{" "}
            {t("Test vakası/suite yönetimi ve matris düzenleme yalnızca")}{" "}
            <strong>Admin</strong>, <strong>Test Lead</strong> {t("ve")}{" "}
            <strong>Tester</strong> {t("rolleri içindir.")}
          </span>
        </section>
      )}

      <section>
        <div className="section-header">
          <div>
            <h2>{t("Test Vakası, Suite ve İzlenebilirlik Yönetimi")}</h2>
            <p className="section-desc">
              {t("Test Tasarımı ve Gerçekleştirme")}
            </p>
          </div>
          <div className="tab-bar" role="tablist" aria-label={t("Test Tasarımı Görünümleri")}>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "cases"}
              className={`tab-btn${activeTab === "cases" ? " active" : ""}`}
              onClick={() => setActiveTab("cases")}
            >
              {t("Test Vakaları")} ({testCases.length})
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "suites"}
              className={`tab-btn${activeTab === "suites" ? " active" : ""}`}
              onClick={() => setActiveTab("suites")}
            >
              {t("Test Suite'ler")} ({suites.length})
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "matrix"}
              className={`tab-btn${activeTab === "matrix" ? " active" : ""}`}
              onClick={() => setActiveTab("matrix")}
            >
              {t("İzlenebilirlik Matrisi")}
            </button>
          </div>
        </div>
      </section>

      {activeTab === "cases" && (
        <>
          {canManage && (
            <section>
              <h3>
                {editingCaseId
                  ? t("Test Vakasını Düzenle ({key})", { key: editingCaseId })
                  : t("Yeni Test Vakası")}
              </h3>
              <form onSubmit={handleCaseSubmit} noValidate className="stacked-form">
                <div className="form-grid">
                  <FormField
                    id="tc-stable-key"
                    label={t("Kararlı Anahtar")}
                    required
                    error={caseFormErrors.stableKey}
                  >
                    <input
                      id="tc-stable-key"
                      value={stableKey}
                      disabled={Boolean(editingCaseId)}
                      onChange={(e) => {
                        setStableKey(e.target.value);
                        if (caseFormErrors.stableKey) {
                          setCaseFormErrors((prev) => ({ ...prev, stableKey: undefined }));
                        }
                      }}
                      placeholder={t("Örn: TC-007")}
                    />
                  </FormField>

                  <FormField
                    id="tc-title"
                    label={t("Test Vakası Başlığı")}
                    required
                    error={caseFormErrors.title}
                  >
                    <input
                      id="tc-title"
                      value={caseTitle}
                      onChange={(e) => {
                        setCaseTitle(e.target.value);
                        if (caseFormErrors.title) {
                          setCaseFormErrors((prev) => ({ ...prev, title: undefined }));
                        }
                      }}
                      placeholder={t("Örn: Sürüm çıkış kapısı doğrulaması")}
                    />
                  </FormField>

                  <FormField
                    id="tc-priority"
                    label={t("Öncelik")}
                    required
                    error={caseFormErrors.priority}
                  >
                    <select
                      id="tc-priority"
                      value={casePriority}
                      onChange={(e) => setCasePriority(e.target.value as TestPriority)}
                    >
                      {TEST_PRIORITIES.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </FormField>

                  <FormField id="tc-suite" label={t("Test Suite")}>
                    <select
                      id="tc-suite"
                      value={caseSuiteId}
                      onChange={(e) => setCaseSuiteId(e.target.value)}
                    >
                      <option value="">{t("Suite atanmadı")}</option>
                      {suites.map((s) => (
                        <option key={s.id} value={String(s.id)}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </FormField>
                </div>

                <div className="form-grid">
                  <FormField
                    id="tc-steps"
                    label={t("Test Adımları (her satıra bir adım)")}
                    required
                    error={caseFormErrors.stepsText}
                  >
                    <textarea
                      id="tc-steps"
                      rows={3}
                      value={stepsText}
                      onChange={(e) => {
                        setStepsText(e.target.value);
                        if (caseFormErrors.stepsText) {
                          setCaseFormErrors((prev) => ({ ...prev, stepsText: undefined }));
                        }
                      }}
                      placeholder={t(
                        "1. İlgili ekranı açın\n2. Geçerli veriyi gönderin\n3. Yanıtı doğrulayın",
                      )}
                    />
                  </FormField>

                  <FormField
                    id="tc-expected"
                    label={t("Beklenen Sonuç")}
                    required
                    error={caseFormErrors.expectedResult}
                  >
                    <textarea
                      id="tc-expected"
                      rows={3}
                      value={expectedResult}
                      onChange={(e) => {
                        setExpectedResult(e.target.value);
                        if (caseFormErrors.expectedResult) {
                          setCaseFormErrors((prev) => ({ ...prev, expectedResult: undefined }));
                        }
                      }}
                      placeholder={t("Örn: HTTP 201 döner ve kayıt listede görünür.")}
                    />
                  </FormField>
                </div>

                <div className="trace-panel">
                  <div className="trace-panel-header">
                    <strong>
                      {t("Bağlı Gereksinimler")} <span className="required-mark">*</span>
                    </strong>
                    <span className="hint">
                      {t("FR-REQ-01 gereği her test vakası en az bir gereksinime bağlanmalıdır.")}
                    </span>
                    {caseFormErrors.requirements && (
                      <span className="field-error" role="alert">
                        {caseFormErrors.requirements}
                      </span>
                    )}
                  </div>
                  <div className="trace-checkbox-grid">
                    {requirements.map((req) => {
                      const checked = caseRequirements.includes(req.id);
                      return (
                        <label key={req.id} className="trace-checkbox-item">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) => {
                              setCaseRequirements((prev) =>
                                e.target.checked
                                  ? [...prev, req.id]
                                  : prev.filter((id) => id !== req.id),
                              );
                              if (caseFormErrors.requirements) {
                                setCaseFormErrors((prev) => ({ ...prev, requirements: undefined }));
                              }
                            }}
                          />
                          <span>
                            <strong>{req.id}</strong> · {req.title}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </div>

                <div className="inline-controls">
                  <label className="checkbox-inline">
                    <input
                      type="checkbox"
                      checked={isAutomated}
                      onChange={(e) => setIsAutomated(e.target.checked)}
                    />
                    <span>{t("Otomatikleştirilmiş test vakası (CI/CD ile koşulur)")}</span>
                  </label>
                  <div className="row-actions">
                    <button type="submit" disabled={saving}>
                      {editingCaseId ? t("Güncelle") : t("Test Vakası Ekle")}
                    </button>
                    {editingCaseId && (
                      <button type="button" className="secondary-btn" onClick={resetCaseForm}>
                        {t("İptal")}
                      </button>
                    )}
                  </div>
                </div>
              </form>
            </section>
          )}

          <section>
            <div className="section-header">
              <h3>{t("Test Vakası Kataloğu")}</h3>
              <div className="filter-group">
                <input
                  aria-label={t("Test vakası ara")}
                  placeholder={t("Anahtar veya başlık ara...")}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <select
                  aria-label={t("Önceliğe göre filtrele")}
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                >
                  <option value="all">{t("Tüm Öncelikler")}</option>
                  {TEST_PRIORITIES.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
                <select
                  aria-label={t("Otomasyona göre filtrele")}
                  value={automationFilter}
                  onChange={(e) => setAutomationFilter(e.target.value)}
                >
                  <option value="all">{t("Otomatik + Manuel")}</option>
                  <option value="auto">{t("Yalnızca Otomatik")}</option>
                  <option value="manual">{t("Yalnızca Manuel")}</option>
                </select>
                <select
                  aria-label={t("Suite'e göre filtrele")}
                  value={suiteFilter}
                  onChange={(e) => setSuiteFilter(e.target.value)}
                >
                  <option value="all">{t("Tüm Suite'ler")}</option>
                  {suites.map((s) => (
                    <option key={s.id} value={String(s.id)}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {loading ? (
              <p className="hint">{t("Yükleniyor...")}</p>
            ) : (
              <DataTable
                columns={testCaseColumns}
                rows={filteredCases}
                getRowKey={(tc) => tc.id}
                emptyMessage="Filtrelerle eşleşen test vakası bulunamadı."
                ariaLabel="Test Vakaları Kataloğu"
              />
            )}

            {expandedCase && (
              <div className="case-detail-drawer" aria-label={t("Test Vakası Adım Detayları")}>
                <div className="detail-title-row">
                  <h3>
                    {expandedCase.stable_key ?? expandedCase.id} · {expandedCase.title}
                  </h3>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => setExpandedCaseId(null)}
                  >
                    {t("Kapat")}
                  </button>
                </div>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">{t("Test Adımları (Test Procedure)")}</span>
                    {expandedCase.steps && expandedCase.steps.length > 0 ? (
                      <ol className="steps-list">
                        {expandedCase.steps.map((step, idx) => (
                          <li key={idx}>{step}</li>
                        ))}
                      </ol>
                    ) : (
                      <span className="hint">{t("Adım bilgisi tanımlanmamış.")}</span>
                    )}
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">{t("Beklenen Sonuç (Expected Result)")}</span>
                    <p className="expected-text">
                      {expandedCase.expected_result || t("Tanımlanmamış.")}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </section>
        </>
      )}

      {activeTab === "suites" && (
        <section>
          <h3>{editingSuiteId !== null ? t("Test Suite Düzenle") : t("Yeni Test Suite")}</h3>

          {canManage && (
            <form onSubmit={handleSuiteSubmit} noValidate className="stacked-form">
              <div className="form-grid">
                <FormField
                  id="suite-project"
                  label={t("Proje")}
                  required
                  error={suiteFormErrors.projectId}
                >
                  <select
                    id="suite-project"
                    value={suiteProjectId}
                    onChange={(e) => {
                      setSuiteProjectId(e.target.value);
                      if (suiteFormErrors.projectId) {
                        setSuiteFormErrors((prev) => ({ ...prev, projectId: undefined }));
                      }
                    }}
                  >
                    <option value="">{t("Proje seçin")}</option>
                    {projects.map((p) => (
                      <option key={p.id} value={String(p.id)}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </FormField>

                <FormField
                  id="suite-name"
                  label={t("Suite Adı")}
                  required
                  error={suiteFormErrors.name}
                >
                  <input
                    id="suite-name"
                    value={suiteName}
                    onChange={(e) => {
                      setSuiteName(e.target.value);
                      if (suiteFormErrors.name) {
                        setSuiteFormErrors((prev) => ({ ...prev, name: undefined }));
                      }
                    }}
                    placeholder={t("Örn: Sprint 2 Regresyon Paketi")}
                  />
                </FormField>

                <FormField
                  id="suite-description"
                  label={t("Açıklama")}
                  error={suiteFormErrors.description}
                >
                  <input
                    id="suite-description"
                    value={suiteDescription}
                    onChange={(e) => {
                      setSuiteDescription(e.target.value);
                      if (suiteFormErrors.description) {
                        setSuiteFormErrors((prev) => ({ ...prev, description: undefined }));
                      }
                    }}
                    placeholder={t("Kapsam ve hedef koşum notu")}
                  />
                </FormField>
              </div>

              <div className="trace-panel">
                <div className="trace-panel-header">
                  <strong>{t("Suite İçindeki Test Vakaları")}</strong>
                  <span className="hint">
                    {t("Bu test suite kapsamında koşulacak vakaları seçin.")}
                  </span>
                </div>
                <div className="trace-checkbox-grid">
                  {testCases.map((tc) => {
                    const checked = suiteCaseIds.includes(tc.id);
                    return (
                      <label key={tc.id} className="trace-checkbox-item">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) =>
                            setSuiteCaseIds((prev) =>
                              e.target.checked
                                ? [...prev, tc.id]
                                : prev.filter((id) => id !== tc.id),
                            )
                          }
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
                  {editingSuiteId !== null ? t("Suite Güncelle") : t("Suite Oluştur")}
                </button>
                {editingSuiteId !== null && (
                  <button type="button" className="secondary-btn" onClick={resetSuiteForm}>
                    {t("İptal")}
                  </button>
                )}
              </div>
            </form>
          )}

          <DataTable
            columns={suiteColumns}
            rows={suites}
            getRowKey={(s) => s.id}
            emptyMessage="Henüz tanımlı test suite yok."
            ariaLabel="Test Suite Listesi"
          />
        </section>
      )}

      {activeTab === "matrix" && (
        <>
          <section className="metrics">
            <div className="card">
              <span>{t("Toplam Gereksinim")}</span>
              <strong>{matrixStats.totalReqs}</strong>
            </div>
            <div className="card">
              <span>{t("Kapsanan Gereksinim")}</span>
              <strong>{matrixStats.coveredCount}</strong>
            </div>
            <div className="card">
              <span>{t("Gereksinim Kapsamı")}</span>
              <strong>{matrixStats.coverageRate}%</strong>
            </div>
            <div className="card">
              <span>{t("Toplam İzlenebilirlik Bağı")}</span>
              <strong>{matrixStats.totalLinks}</strong>
            </div>
          </section>

          <section>
            <div className="section-header">
              <div>
                <h3>{t("Gereksinim – Test İzlenebilirlik Matrisi")}</h3>
                <p className="section-desc">
                  {t("Her satır bir gereksinimi, her sütun bir test vakasını temsil eder.")}{" "}
                  {canManage
                    ? t("Hücrelere tıklayarak bağlantıyı doğrudan güncelleyebilirsiniz.")
                    : t("Salt okunur görünüm.")}
                </p>
              </div>
              <div className="filter-group">
                <label htmlFor="matrix-project-filter">{t("Proje:")}</label>
                <select
                  id="matrix-project-filter"
                  value={matrixProjectFilter}
                  onChange={(e) => setMatrixProjectFilter(e.target.value)}
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

            {matrixStats.uncoveredReqs.length > 0 && (
              <div className="gap-alert" role="status">
                <strong>{t("Kapsam Eksikliği (Gap):")}</strong>{" "}
                {t("{requirements} gereksinimlerine henüz test vakası bağlanmamış.", {
                  requirements: matrixStats.uncoveredReqs.map((r) => r.id).join(", "),
                })}
              </div>
            )}

            {filteredRequirements.length === 0 || testCases.length === 0 ? (
              <p className="table-empty">
                {t("Matris oluşturmak için en az bir gereksinim ve bir test vakası bulunmalıdır.")}
              </p>
            ) : (
              <div className="matrix-scroll">
                <table className="matrix-table" aria-label={t("Gereksinim Test İzlenebilirlik Matrisi")}>
                  <thead>
                    <tr>
                      <th className="matrix-sticky-col">{t("Gereksinim")}</th>
                      <th>{t("Özet (P / F / B / NR)")}</th>
                      {testCases.map((tc) => (
                        <th key={tc.id} title={`${tc.stable_key ?? tc.id}: ${tc.title}`}>
                          <div className="matrix-col-header">
                            <span>{tc.stable_key ?? tc.id}</span>
                            <StatusBadge text={tc.status} />
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRequirements.map((req) => {
                      const linkedCases = testCases.filter((tc) =>
                        tc.requirements.includes(req.id),
                      );
                      const passedCount = linkedCases.filter((c) => c.status === "Passed").length;
                      const failedCount = linkedCases.filter((c) => c.status === "Failed").length;
                      const blockedCount = linkedCases.filter(
                        (c) => c.status === "Blocked",
                      ).length;
                      const notRunCount = linkedCases.filter(
                        (c) => c.status === "Not Run" || c.status === "Skipped",
                      ).length;

                      return (
                        <tr key={req.id}>
                          <td className="matrix-sticky-col">
                            <strong>{req.id}</strong> · {req.title}
                            {linkedCases.length === 0 && (
                              <span className="badge gap-badge">{t("Kapsamsız")}</span>
                            )}
                          </td>
                          <td>
                            <span className="matrix-summary">
                              {t("{count} test", { count: linkedCases.length })} ({passedCount}/
                              {failedCount}/{blockedCount}/
                              {notRunCount})
                            </span>
                          </td>
                          {testCases.map((tc) => {
                            const linked = tc.requirements.includes(req.id);
                            const cellKey = `${req.id}::${tc.id}`;
                            const isBusy = matrixSavingCell === cellKey;
                            return (
                              <td key={tc.id} className="matrix-cell">
                                <button
                                  type="button"
                                  disabled={!canManage || isBusy}
                                  className={`matrix-cell-btn${linked ? " linked" : ""}`}
                                  aria-label={t("{req} ve {caseKey} bağlantısı: {state}", {
                                    req: req.id,
                                    caseKey: tc.stable_key ?? tc.id,
                                    state: linked ? t("Bağlı") : t("Bağlı değil"),
                                  })}
                                  aria-pressed={linked}
                                  onClick={() => void handleMatrixToggle(req, tc, !linked)}
                                >
                                  {isBusy ? "…" : linked ? "✓" : "—"}
                                </button>
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}
