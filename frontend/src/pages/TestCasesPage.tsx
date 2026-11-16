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

type ActiveTab = "cases" | "suites" | "matrix";

export type TestCasesPageProps = {
  user: User | null;
};

export function TestCasesPage({ user }: TestCasesPageProps) {
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
        formatErrorMessage(err, "Test vakaları ve izlenebilirlik verileri yüklenemedi."),
      );
    } finally {
      setLoading(false);
    }
  }, []);

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
    setIsAutomated(Boolean(tc.is_automated));
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
      stable_key: stableKey.trim(),
      title: caseTitle.trim(),
      priority: casePriority,
      is_automated: isAutomated,
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
        await api.createTestCase({ id: payload.stable_key, ...payload });
      }
      resetCaseForm();
      setNotice("Test vakası kaydedildi.");
      setError("");
      await loadData();
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        savePreviewTestCase(payload, editingCaseId, serverCaseIds);
        setPreviewMode(true);
        resetCaseForm();
        setNotice(
          "PLN-16 test vakası CRUD uç noktası henüz backend'de aktif değil; değişiklik yerel önizleme deposuna kaydedildi.",
        );
        setError("");
        await loadData();
      } else {
        setError(formatErrorMessage(err, "Test vakası kaydedilemedi."));
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
      setNotice(`${tc.stable_key ?? tc.id} silindi.`);
      setError("");
      await loadData();
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        deletePreviewTestCase(tc.id);
        setPreviewMode(true);
        if (editingCaseId === tc.id) resetCaseForm();
        if (expandedCaseId === tc.id) setExpandedCaseId(null);
        setNotice(`${tc.stable_key ?? tc.id} yerel önizleme deposundan kaldırıldı.`);
        setError("");
        await loadData();
      } else {
        setError(formatErrorMessage(err, "Test vakası silinemedi."));
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
    setSuiteCaseIds(suite.test_case_ids);
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
      test_case_ids: suiteCaseIds,
    };

    setSaving(true);
    try {
      if (editingSuiteId !== null) {
        await api.updateTestSuite(editingSuiteId, payload);
      } else {
        await api.createTestSuite(payload);
      }
      resetSuiteForm();
      setNotice("Test suite kaydedildi.");
      setError("");
      await loadData();
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        savePreviewTestSuite(payload, editingSuiteId, projects);
        setPreviewMode(true);
        resetSuiteForm();
        setNotice(
          "PLN-16 test suite CRUD uç noktası henüz backend'de aktif değil; suite yerel önizleme deposuna kaydedildi.",
        );
        setError("");
        await loadData();
      } else {
        setError(formatErrorMessage(err, "Test suite kaydedilemedi."));
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
      setNotice(`${suite.name} silindi.`);
      setError("");
      await loadData();
    } catch (err) {
      if (isEndpointUnavailableError(err)) {
        deletePreviewTestSuite(suite.id, projects);
        setPreviewMode(true);
        if (editingSuiteId === suite.id) resetSuiteForm();
        setNotice(`${suite.name} yerel önizleme deposundan silindi.`);
        setError("");
        await loadData();
      } else {
        setError(formatErrorMessage(err, "Test suite silinemedi."));
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleMatrixToggle(req: Requirement, tc: TestCase, currentlyLinked: boolean) {
    if (!canManage) return;

    if (currentlyLinked && tc.requirements.length <= 1) {
      setError(
        `FR-REQ-01 gereği ${tc.stable_key ?? tc.id} en az bir gereksinime bağlı kalmalıdır.`,
      );
      return;
    }

    const cellKey = `${req.id}::${tc.id}`;
    setMatrixSavingCell(cellKey);
    try {
      if (serverCaseIds.has(tc.id)) {
        const nextLinkedForReq = currentlyLinked
          ? req.test_cases.filter((id) => id !== tc.id)
          : Array.from(new Set([...req.test_cases, tc.id]));
        await api.setRequirementTestCases(req.id, nextLinkedForReq);
      }
      if (previewMode || !serverCaseIds.has(tc.id)) {
        togglePreviewRequirementLink(req.id, tc.id, !currentlyLinked);
      }
      setError("");
      await loadData();
    } catch (err) {
      setError(formatErrorMessage(err, "İzlenebilirlik bağlantısı güncellenemedi."));
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
      if (automationFilter === "auto" && !tc.is_automated) return false;
      if (automationFilter === "manual" && tc.is_automated) return false;
      if (suiteFilter !== "all") {
        const suiteObj = suites.find((s) => String(s.id) === suiteFilter);
        const inSuite =
          String(tc.suite_id ?? "") === suiteFilter ||
          Boolean(suiteObj?.test_case_ids.includes(tc.id));
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
      header: "Anahtar",
      render: (tc) => <code>{tc.stable_key ?? tc.id}</code>,
    },
    { key: "title", header: "Başlık", render: (tc) => tc.title },
    {
      key: "priority",
      header: "Öncelik",
      render: (tc) => <StatusBadge text={tc.priority ?? "Medium"} />,
    },
    {
      key: "automation",
      header: "Otomasyon",
      render: (tc) => (
        <span className={`badge ${tc.is_automated ? "auto-yes" : "auto-no"}`}>
          {tc.is_automated ? "Otomatik" : "Manuel"}
        </span>
      ),
    },
    {
      key: "suite",
      header: "Suite",
      render: (tc) => {
        const matchedSuite =
          (tc.suite_id ? suiteNames.get(tc.suite_id) : undefined) ??
          suites.find((s) => s.test_case_ids.includes(tc.id))?.name;
        return matchedSuite ?? <span className="hint">—</span>;
      },
    },
    {
      key: "requirements",
      header: "Gereksinimler",
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
      header: "Son Durum",
      render: (tc) => <StatusBadge text={tc.status} />,
    },
    {
      key: "actions",
      header: "İşlemler",
      render: (tc) => (
        <div className="row-actions">
          <button
            type="button"
            className="secondary-btn"
            onClick={() => setExpandedCaseId((prev) => (prev === tc.id ? null : tc.id))}
          >
            {expandedCaseId === tc.id ? "Gizle" : "Adımlar"}
          </button>
          {canManage && (
            <>
              <button
                type="button"
                className="secondary-btn"
                onClick={() => startEditCase(tc)}
              >
                Düzenle
              </button>
              <button
                type="button"
                className="danger-btn"
                disabled={saving}
                onClick={() => void handleDeleteCase(tc)}
              >
                Sil
              </button>
            </>
          )}
        </div>
      ),
    },
  ];

  const suiteColumns: DataTableColumn<TestSuite>[] = [
    { key: "name", header: "Suite Adı", render: (s) => <strong>{s.name}</strong> },
    {
      key: "project",
      header: "Proje",
      render: (s) => projectNames.get(s.project_id) ?? `#${s.project_id}`,
    },
    {
      key: "description",
      header: "Açıklama",
      render: (s) => s.description || <span className="hint">—</span>,
    },
    {
      key: "cases",
      header: "Test Vakaları",
      render: (s) =>
        s.test_case_ids.length > 0 ? (
          <div className="badge-list">
            {s.test_case_ids.map((id) => (
              <span className="badge" key={id}>
                {id}
              </span>
            ))}
          </div>
        ) : (
          <span className="hint">Vaka atanmadı</span>
        ),
    },
    {
      key: "actions",
      header: "İşlemler",
      render: (s) =>
        canManage ? (
          <div className="row-actions">
            <button
              type="button"
              className="secondary-btn"
              onClick={() => startEditSuite(s)}
            >
              Düzenle
            </button>
            <button
              type="button"
              className="danger-btn"
              disabled={saving}
              onClick={() => void handleDeleteSuite(s)}
            >
              Sil
            </button>
          </div>
        ) : (
          <span className="hint">Salt okunur</span>
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
            <strong>Önizleme Modu (PLN-16 Backend Bekleniyor):</strong>{" "}
            Gereksinim listesi ve mevcut test vakaları sunucudan canlı okunur; matris değişiklikleri
            mevcut test vakaları için <code>PUT /api/requirements/&#123;id&#125;/test-cases</code>{" "}
            üzerinden gerçek veritabanına yazılır. Yeni test vakası, adım/öncelik/otomasyon
            alanları ve test suite CRUD işlemleri PLN-16 uç noktaları eklenene kadar yerel tarayıcı
            deposunda tutulur.
          </div>
        </section>
      )}

      {!user && (
        <section className="role-notice">
          <span>
            Test vakası, suite ve izlenebilirlik matrisi düzenleme işlemleri için{" "}
            <Link to="/login">giriş yapın</Link>.
          </span>
        </section>
      )}

      {user && !canManage && (
        <section className="role-notice">
          <span>
            Aktif rol: <StatusBadge text={user.role} /> · Test vakası/suite yönetimi ve matris
            düzenleme yalnızca <strong>Admin</strong>, <strong>Test Lead</strong> ve{" "}
            <strong>Tester</strong> rolleri içindir.
          </span>
        </section>
      )}

      <section>
        <div className="section-header">
          <div>
            <h2>Test Vakası, Suite ve İzlenebilirlik Yönetimi</h2>
            <p className="section-desc">
              ISO/IEC/IEEE 29119-2 · Test Tasarımı ve Gerçekleştirme (R2)
            </p>
          </div>
          <div className="tab-bar" role="tablist" aria-label="Test Tasarımı Görünümleri">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "cases"}
              className={`tab-btn${activeTab === "cases" ? " active" : ""}`}
              onClick={() => setActiveTab("cases")}
            >
              Test Vakaları ({testCases.length})
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "suites"}
              className={`tab-btn${activeTab === "suites" ? " active" : ""}`}
              onClick={() => setActiveTab("suites")}
            >
              Test Suite&apos;ler ({suites.length})
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "matrix"}
              className={`tab-btn${activeTab === "matrix" ? " active" : ""}`}
              onClick={() => setActiveTab("matrix")}
            >
              İzlenebilirlik Matrisi
            </button>
          </div>
        </div>
      </section>

      {activeTab === "cases" && (
        <>
          {canManage && (
            <section>
              <h3>{editingCaseId ? `Test Vakasını Düzenle (${editingCaseId})` : "Yeni Test Vakası"}</h3>
              <form onSubmit={handleCaseSubmit} noValidate className="stacked-form">
                <div className="form-grid">
                  <FormField
                    id="tc-stable-key"
                    label="Kararlı Anahtar"
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
                      placeholder="Örn: TC-007"
                    />
                  </FormField>

                  <FormField
                    id="tc-title"
                    label="Test Vakası Başlığı"
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
                      placeholder="Örn: Sürüm çıkış kapısı doğrulaması"
                    />
                  </FormField>

                  <FormField
                    id="tc-priority"
                    label="Öncelik"
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

                  <FormField id="tc-suite" label="Test Suite">
                    <select
                      id="tc-suite"
                      value={caseSuiteId}
                      onChange={(e) => setCaseSuiteId(e.target.value)}
                    >
                      <option value="">Suite atanmadı</option>
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
                    label="Test Adımları (her satıra bir adım)"
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
                      placeholder={"1. İlgili ekranı açın\n2. Geçerli veriyi gönderin\n3. Yanıtı doğrulayın"}
                    />
                  </FormField>

                  <FormField
                    id="tc-expected"
                    label="Beklenen Sonuç"
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
                      placeholder="Örn: HTTP 201 döner ve kayıt listede görünür."
                    />
                  </FormField>
                </div>

                <div className="trace-panel">
                  <div className="trace-panel-header">
                    <strong>
                      Bağlı Gereksinimler <span className="required-mark">*</span>
                    </strong>
                    <span className="hint">
                      FR-REQ-01 gereği her test vakası en az bir gereksinime bağlanmalıdır.
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
                    <span>Otomatikleştirilmiş test vakası (CI/CD ile koşulur)</span>
                  </label>
                  <div className="row-actions">
                    <button type="submit" disabled={saving}>
                      {editingCaseId ? "Güncelle" : "Test Vakası Ekle"}
                    </button>
                    {editingCaseId && (
                      <button type="button" className="secondary-btn" onClick={resetCaseForm}>
                        İptal
                      </button>
                    )}
                  </div>
                </div>
              </form>
            </section>
          )}

          <section>
            <div className="section-header">
              <h3>Test Vakası Kataloğu</h3>
              <div className="filter-group">
                <input
                  aria-label="Test vakası ara"
                  placeholder="Anahtar veya başlık ara..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <select
                  aria-label="Önceliğe göre filtrele"
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                >
                  <option value="all">Tüm Öncelikler</option>
                  {TEST_PRIORITIES.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Otomasyona göre filtrele"
                  value={automationFilter}
                  onChange={(e) => setAutomationFilter(e.target.value)}
                >
                  <option value="all">Otomatik + Manuel</option>
                  <option value="auto">Yalnızca Otomatik</option>
                  <option value="manual">Yalnızca Manuel</option>
                </select>
                <select
                  aria-label="Suite'e göre filtrele"
                  value={suiteFilter}
                  onChange={(e) => setSuiteFilter(e.target.value)}
                >
                  <option value="all">Tüm Suite&apos;ler</option>
                  {suites.map((s) => (
                    <option key={s.id} value={String(s.id)}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {loading ? (
              <p className="hint">Yükleniyor...</p>
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
              <div className="case-detail-drawer" aria-label="Test Vakası Adım Detayları">
                <div className="detail-title-row">
                  <h3>
                    {expandedCase.stable_key ?? expandedCase.id} · {expandedCase.title}
                  </h3>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => setExpandedCaseId(null)}
                  >
                    Kapat
                  </button>
                </div>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">Test Adımları (Test Procedure)</span>
                    {expandedCase.steps && expandedCase.steps.length > 0 ? (
                      <ol className="steps-list">
                        {expandedCase.steps.map((step, idx) => (
                          <li key={idx}>{step}</li>
                        ))}
                      </ol>
                    ) : (
                      <span className="hint">Adım bilgisi tanımlanmamış.</span>
                    )}
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Beklenen Sonuç (Expected Result)</span>
                    <p className="expected-text">
                      {expandedCase.expected_result || "Tanımlanmamış."}
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
          <h3>{editingSuiteId !== null ? "Test Suite Düzenle" : "Yeni Test Suite"}</h3>

          {canManage && (
            <form onSubmit={handleSuiteSubmit} noValidate className="stacked-form">
              <div className="form-grid">
                <FormField
                  id="suite-project"
                  label="Proje"
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
                    <option value="">Proje seçin</option>
                    {projects.map((p) => (
                      <option key={p.id} value={String(p.id)}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </FormField>

                <FormField
                  id="suite-name"
                  label="Suite Adı"
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
                    placeholder="Örn: Sprint 2 Regresyon Paketi"
                  />
                </FormField>

                <FormField
                  id="suite-description"
                  label="Açıklama"
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
                    placeholder="Kapsam ve hedef koşum notu"
                  />
                </FormField>
              </div>

              <div className="trace-panel">
                <div className="trace-panel-header">
                  <strong>Suite İçindeki Test Vakaları</strong>
                  <span className="hint">Bu test suite kapsamında koşulacak vakaları seçin.</span>
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
                  {editingSuiteId !== null ? "Suite Güncelle" : "Suite Oluştur"}
                </button>
                {editingSuiteId !== null && (
                  <button type="button" className="secondary-btn" onClick={resetSuiteForm}>
                    İptal
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
              <span>Toplam Gereksinim</span>
              <strong>{matrixStats.totalReqs}</strong>
            </div>
            <div className="card">
              <span>Kapsanan Gereksinim</span>
              <strong>{matrixStats.coveredCount}</strong>
            </div>
            <div className="card">
              <span>Gereksinim Kapsamı</span>
              <strong>{matrixStats.coverageRate}%</strong>
            </div>
            <div className="card">
              <span>Toplam İzlenebilirlik Bağı</span>
              <strong>{matrixStats.totalLinks}</strong>
            </div>
          </section>

          <section>
            <div className="section-header">
              <div>
                <h3>Gereksinim – Test İzlenebilirlik Matrisi (R2)</h3>
                <p className="section-desc">
                  Her satır bir gereksinimi, her sütun bir test vakasını temsil eder.{" "}
                  {canManage
                    ? "Hücrelere tıklayarak bağlantıyı doğrudan güncelleyebilirsiniz."
                    : "Salt okunur görünüm."}
                </p>
              </div>
              <div className="filter-group">
                <label htmlFor="matrix-project-filter">Proje:</label>
                <select
                  id="matrix-project-filter"
                  value={matrixProjectFilter}
                  onChange={(e) => setMatrixProjectFilter(e.target.value)}
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

            {matrixStats.uncoveredReqs.length > 0 && (
              <div className="gap-alert" role="status">
                <strong>Kapsam Eksikliği (Gap):</strong>{" "}
                {matrixStats.uncoveredReqs.map((r) => r.id).join(", ")} gereksinimlerine henüz
                test vakası bağlanmamış.
              </div>
            )}

            {filteredRequirements.length === 0 || testCases.length === 0 ? (
              <p className="table-empty">
                Matris oluşturmak için en az bir gereksinim ve bir test vakası bulunmalıdır.
              </p>
            ) : (
              <div className="matrix-scroll">
                <table className="matrix-table" aria-label="Gereksinim Test İzlenebilirlik Matrisi">
                  <thead>
                    <tr>
                      <th className="matrix-sticky-col">Gereksinim</th>
                      <th>Özet (P / F / B / NR)</th>
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
                              <span className="badge gap-badge">Kapsamsız</span>
                            )}
                          </td>
                          <td>
                            <span className="matrix-summary">
                              {linkedCases.length} test ({passedCount}/{failedCount}/{blockedCount}/
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
                                  aria-label={`${req.id} ve ${tc.stable_key ?? tc.id} bağlantısı: ${
                                    linked ? "Bağlı" : "Bağlı değil"
                                  }`}
                                  aria-pressed={linked}
                                  onClick={() => void handleMatrixToggle(req, tc, linked)}
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
