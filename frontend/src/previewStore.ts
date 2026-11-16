import {
  CreateTestRunPayload,
  Defect,
  ExecutionStatus,
  Project,
  RecordExecutionPayload,
  Release,
  TestCase,
  TestCaseCreateInput,
  TestExecution,
  TestPriority,
  TestRun,
  TestSuite,
  TestSuitePayload,
} from "./api";

const PLN19_STORAGE_KEY = "sds06:preview:pln19:v1";
const PLN20_STORAGE_KEY = "sds06:preview:pln20:v1";

type StoredPln19State = {
  testCaseOverrides: Record<
    string,
    {
      stable_key?: string;
      title?: string;
      steps?: string[];
      expected_result?: string;
      priority?: TestPriority;
      automated?: boolean;
      requirements?: string[];
      suite_id?: number | null;
    }
  >;
  localTestCases: TestCase[];
  deletedTestCaseIds: string[];
  suites: TestSuite[] | null;
  nextSuiteId: number;
};

type StoredPln20State = {
  runs: TestRun[] | null;
  nextRunId: number;
  nextExecutionId: number;
};

const SEED_CASE_DETAILS: Record<
  string,
  {
    steps: string[];
    expected_result: string;
    priority: TestPriority;
    automated: boolean;
    suite_id: number;
  }
> = {
  "TC-001": {
    steps: [
      "Giriş ekranını (/login) açın.",
      "Geçerli kullanıcı adı (tester) ve parola (demo1234) girin.",
      "Giriş Yap düğmesine tıklayın.",
    ],
    expected_result: "JWT erişim belirteci döner ve kullanıcı ana panele yönlendirilir.",
    priority: "Critical",
    automated: true,
    suite_id: 1,
  },
  "TC-002": {
    steps: [
      "Giriş ekranını açın.",
      "Geçerli kullanıcı adı ve hatalı parola girin.",
      "Giriş Yap düğmesine tıklayın.",
    ],
    expected_result: "API HTTP 401 döner ve ekranda kimlik doğrulama hata mesajı gösterilir.",
    priority: "High",
    automated: true,
    suite_id: 1,
  },
  "TC-003": {
    steps: [
      "Tester rolü ile oturum açın.",
      "Defect oluşturma formunda başlık alanını boş veya 3 karakterden kısa bırakın.",
      "Ekle düğmesine tıklayın.",
    ],
    expected_result: "Doğrulama hatası gösterilir ve yeni defect kaydı oluşturulmaz.",
    priority: "High",
    automated: false,
    suite_id: 2,
  },
  "TC-004": {
    steps: [
      "Developer ve Tester hesaplarıyla aynı defect kaydını inceleyin.",
      "İzin verilen durum geçişlerini (Open → In Progress → Resolved → Closed) tetikleyin.",
      "Yetkisiz rolde geçiş deneyin.",
    ],
    expected_result: "İzin verilen geçişler geçmişe eklenir; yetkisiz geçiş 403 ile reddedilir.",
    priority: "Critical",
    automated: true,
    suite_id: 2,
  },
  "TC-005": {
    steps: [
      "Projeler ve test koşumları verisini hazırlayın.",
      "Test özet raporu üretimini tetikleyin.",
    ],
    expected_result: "Türkçe karakterler korunarak IEEE 829 Test Summary Report üretilir.",
    priority: "Medium",
    automated: false,
    suite_id: 3,
  },
  "TC-006": {
    steps: [
      "Geçerli bir JUnit XML dosyası seçin.",
      "İçe aktarım uç noktasına dosyayı yükleyin.",
    ],
    expected_result: "Test sonuçları ayrıştırılır ve eşleşen test vakalarının durumu güncellenir.",
    priority: "Medium",
    automated: true,
    suite_id: 3,
  },
};

function defaultSuites(projects: Project[]): TestSuite[] {
  const defaultProjectId = projects[0]?.id ?? 1;
  return [
    {
      id: 1,
      project_id: defaultProjectId,
      name: "Kimlik Doğrulama & Yetkilendirme Smoke",
      description: "R1 giriş, JWT oturum ve rol doğrulama vakaları",
      test_cases: ["TC-001", "TC-002"],
    },
    {
      id: 2,
      project_id: defaultProjectId,
      name: "Defect Yaşam Döngüsü Regresyon",
      description: "R3 ve R4 defect oluşturma ve geçiş kuralları",
      test_cases: ["TC-003", "TC-004"],
    },
    {
      id: 3,
      project_id: defaultProjectId,
      name: "Raporlama & CI İçe Aktarım",
      description: "R6 ve R7 özet rapor ve JUnit XML doğrulama vakaları",
      test_cases: ["TC-005", "TC-006"],
    },
  ];
}

function readState(): StoredPln19State {
  try {
    const raw = localStorage.getItem(PLN19_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<StoredPln19State>;
      return {
        testCaseOverrides: parsed.testCaseOverrides ?? {},
        localTestCases: parsed.localTestCases ?? [],
        deletedTestCaseIds: parsed.deletedTestCaseIds ?? [],
        suites: parsed.suites ?? null,
        nextSuiteId: parsed.nextSuiteId ?? 4,
      };
    }
  } catch {
    // Bozuk localStorage kaydı durumunda varsayılan duruma dön
  }
  return {
    testCaseOverrides: {},
    localTestCases: [],
    deletedTestCaseIds: [],
    suites: null,
    nextSuiteId: 4,
  };
}

function writeState(state: StoredPln19State): void {
  try {
    localStorage.setItem(PLN19_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Depolama kotası veya gizli mod durumunda sessizce devam et
  }
}

export function mergeTestCasesWithPreview(serverCases: TestCase[]): TestCase[] {
  const state = readState();
  const deleted = new Set(state.deletedTestCaseIds);

  const mergedServer = serverCases
    .filter((tc) => !deleted.has(tc.id))
    .map((tc) => {
      const seed = SEED_CASE_DETAILS[tc.id];
      const override = state.testCaseOverrides[tc.id];
      const reqs =
        override?.requirements && override.requirements.length > 0
          ? override.requirements
          : tc.requirements && tc.requirements.length > 0
            ? tc.requirements
            : tc.requirement
              ? [tc.requirement]
              : [];

      return {
        ...tc,
        stable_key: tc.stable_key ?? override?.stable_key ?? tc.id,
        title: override?.title ?? tc.title,
        steps:
          tc.steps && tc.steps.length > 0
            ? tc.steps
            : override?.steps ??
              seed?.steps ?? ["Ön koşulları doğrulayın ve test adımlarını uygulayın."],
        expected_result:
          tc.expected_result ||
          override?.expected_result ||
          seed?.expected_result ||
          "Beklenen sistem davranışı gözlemlenir.",
        priority: tc.priority ?? override?.priority ?? seed?.priority ?? "Medium",
        automated: tc.automated ?? override?.automated ?? seed?.automated ?? false,
        suite_id: tc.suite_id ?? override?.suite_id ?? seed?.suite_id ?? null,
        requirements: reqs,
        requirement: reqs[0] ?? tc.requirement,
      };
    });

  const serverIds = new Set(mergedServer.map((tc) => tc.id));
  const localOnly = state.localTestCases
    .filter((tc) => !deleted.has(tc.id) && !serverIds.has(tc.id))
    .map((tc) => {
      const override = state.testCaseOverrides[tc.id];
      const reqs = override?.requirements ?? tc.requirements;
      return {
        ...tc,
        ...override,
        requirements: reqs,
        requirement: reqs[0] ?? tc.requirement,
      };
    });

  return [...mergedServer, ...localOnly];
}

export function savePreviewTestCase(
  payload: TestCaseCreateInput,
  editingId: string | null,
  serverIds: Set<string>,
): TestCase {
  const state = readState();
  const key = (editingId ?? payload.id).trim();
  const steps = payload.steps ?? [];
  const expectedResult = (payload.expected_result ?? "").trim();
  const priority = payload.priority ?? "Medium";
  const automated = payload.automated ?? false;

  if (editingId && serverIds.has(editingId)) {
    state.testCaseOverrides[editingId] = {
      stable_key: payload.id.trim(),
      title: payload.title.trim(),
      steps,
      expected_result: expectedResult,
      priority,
      automated,
      requirements: payload.requirements,
      suite_id: payload.suite_id ?? null,
    };
    writeState(state);
    return {
      id: editingId,
      stable_key: payload.id.trim(),
      title: payload.title.trim(),
      steps,
      expected_result: expectedResult,
      priority,
      automated,
      requirements: payload.requirements,
      requirement: payload.requirements[0] ?? "",
      status: "Not Run",
      suite_id: payload.suite_id ?? null,
    };
  }

  const created: TestCase = {
    id: key,
    stable_key: payload.id.trim(),
    title: payload.title.trim(),
    steps,
    expected_result: expectedResult,
    priority,
    automated,
    requirements: payload.requirements,
    requirement: payload.requirements[0] ?? "",
    status: "Not Run",
    suite_id: payload.suite_id ?? null,
  };

  state.deletedTestCaseIds = state.deletedTestCaseIds.filter((id) => id !== key);
  const existingIdx = state.localTestCases.findIndex((tc) => tc.id === key);
  if (existingIdx >= 0) {
    created.status = state.localTestCases[existingIdx].status;
    state.localTestCases[existingIdx] = created;
  } else {
    state.localTestCases.push(created);
  }
  delete state.testCaseOverrides[key];
  writeState(state);
  return created;
}

export function deletePreviewTestCase(id: string): void {
  const state = readState();
  state.localTestCases = state.localTestCases.filter((tc) => tc.id !== id);
  delete state.testCaseOverrides[id];
  if (!state.deletedTestCaseIds.includes(id)) {
    state.deletedTestCaseIds.push(id);
  }
  if (state.suites) {
    state.suites = state.suites.map((suite) => ({
      ...suite,
      test_cases: suite.test_cases.filter((tcId) => tcId !== id),
    }));
  }
  writeState(state);
}

export function loadPreviewTestSuites(projects: Project[]): TestSuite[] {
  const state = readState();
  if (state.suites !== null) {
    return state.suites;
  }
  const seeded = defaultSuites(projects);
  state.suites = seeded;
  writeState(state);
  return seeded;
}

export function savePreviewTestSuite(
  payload: TestSuitePayload,
  editingId: number | null,
  projects: Project[],
): TestSuite {
  const state = readState();
  const current = state.suites ?? defaultSuites(projects);

  if (editingId !== null) {
    const updated: TestSuite = {
      id: editingId,
      project_id: payload.project_id,
      name: payload.name.trim(),
      description: payload.description.trim(),
      test_cases: payload.test_cases ?? [],
    };
    state.suites = current.map((s) => (s.id === editingId ? updated : s));
    writeState(state);
    return updated;
  }

  const created: TestSuite = {
    id: state.nextSuiteId,
    project_id: payload.project_id,
    name: payload.name.trim(),
    description: payload.description.trim(),
    test_cases: payload.test_cases ?? [],
  };
  state.nextSuiteId += 1;
  state.suites = [...current, created];
  writeState(state);
  return created;
}

export function deletePreviewTestSuite(id: number, projects: Project[]): void {
  const state = readState();
  const current = state.suites ?? defaultSuites(projects);
  state.suites = current.filter((s) => s.id !== id);
  writeState(state);
}

export function togglePreviewRequirementLink(
  reqId: string,
  tcId: string,
  linked: boolean,
): void {
  const state = readState();
  const target = state.localTestCases.find((tc) => tc.id === tcId);
  if (target) {
    const nextReqs = linked
      ? Array.from(new Set([...target.requirements, reqId]))
      : target.requirements.filter((r) => r !== reqId);
    target.requirements = nextReqs;
    target.requirement = nextReqs[0] ?? "";
    writeState(state);
    return;
  }

  const existing = state.testCaseOverrides[tcId] ?? {};
  const currentReqs = existing.requirements ?? [];
  const nextReqs = linked
    ? Array.from(new Set([...currentReqs, reqId]))
    : currentReqs.filter((r) => r !== reqId);
  state.testCaseOverrides[tcId] = {
    ...existing,
    requirements: nextReqs,
  };
  writeState(state);
}

// --- PLN-20: Test Run & Execution Preview Store ---

function readRunState(): StoredPln20State {
  try {
    const raw = localStorage.getItem(PLN20_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<StoredPln20State>;
      return {
        runs: parsed.runs ?? null,
        nextRunId: parsed.nextRunId ?? 4,
        nextExecutionId: parsed.nextExecutionId ?? 100,
      };
    }
  } catch {
    // Bozuk localStorage kaydı durumunda varsayılan duruma dön
  }
  return {
    runs: null,
    nextRunId: 4,
    nextExecutionId: 100,
  };
}

function writeRunState(state: StoredPln20State): void {
  try {
    localStorage.setItem(PLN20_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Depolama kotası veya gizli mod durumunda sessizce devam et
  }
}

function buildSeedExecution(
  id: number,
  runId: number,
  testCaseId: string,
  status: ExecutionStatus,
  actualResult: string,
  notes: string,
  executedBy: string | null,
  executedAt: string | null,
  defectIds: number[] = [],
): TestExecution {
  return {
    id,
    run_id: runId,
    test_case_id: testCaseId,
    status,
    actual_result: actualResult,
    notes,
    executed_by: executedBy,
    executed_at: executedAt,
    defect_ids: defectIds,
  };
}

function defaultTestRuns(
  projects: Project[],
  releases: Release[],
  testCases: TestCase[],
  defects: Defect[],
): TestRun[] {
  const projectId = projects[0]?.id ?? 1;
  const releaseId = releases[0]?.id ?? null;
  const tcSet = new Set(testCases.map((tc) => tc.id));

  const defectForTc3 = defects.find((d) => d.test_case === "TC-003")?.id;
  const defectForTc5 = defects.find((d) => d.test_case === "TC-005")?.id;

  const run1Candidates: TestExecution[] = [
    buildSeedExecution(
      1,
      1,
      "TC-001",
      "Passed",
      "JWT token üretildi, kullanıcı ana sayfaya yönlendirildi.",
      "Sprint 1 smoke koşumu",
      "tester",
      "2026-11-10T10:15:00Z",
    ),
    buildSeedExecution(
      2,
      1,
      "TC-002",
      "Passed",
      "HTTP 401 ve Türkçe hata mesajı doğrulandı.",
      "",
      "tester",
      "2026-11-10T10:22:00Z",
    ),
    buildSeedExecution(
      3,
      1,
      "TC-003",
      "Failed",
      "Boş başlık gönderiminde istemci doğrulaması atlandı.",
      "Defect #1 ile izleniyor.",
      "tester",
      "2026-11-10T10:35:00Z",
      defectForTc3 ? [defectForTc3] : [],
    ),
    buildSeedExecution(
      4,
      1,
      "TC-004",
      "Blocked",
      "Önceki adım olan TC-003 başarısız olduğu için ertelendi.",
      "",
      "tester",
      "2026-11-10T10:40:00Z",
    ),
  ];

  const run2Candidates: TestExecution[] = [
    buildSeedExecution(
      5,
      2,
      "TC-001",
      "Passed",
      "Otomatik smoke test başarılı.",
      "",
      "tester",
      "2026-11-12T14:05:00Z",
    ),
    buildSeedExecution(
      6,
      2,
      "TC-002",
      "Passed",
      "401 yanıtı doğrulandı.",
      "",
      "tester",
      "2026-11-12T14:08:00Z",
    ),
    buildSeedExecution(
      7,
      2,
      "TC-003",
      "Failed",
      "Doğrulama düzeltmesi henüz birleştirilmedi.",
      "",
      "tester",
      "2026-11-12T14:15:00Z",
      defectForTc3 ? [defectForTc3] : [],
    ),
    buildSeedExecution(
      8,
      2,
      "TC-004",
      "Passed",
      "Rol bazlı tüm geçişler doğrulandı.",
      "",
      "testlead",
      "2026-11-12T14:25:00Z",
    ),
    buildSeedExecution(
      9,
      2,
      "TC-005",
      "Skipped",
      "PDF şablon görevi sonraki sprinte bırakıldı.",
      defectForTc5 ? `İlişkili defect #${defectForTc5}` : "",
      "testlead",
      "2026-11-12T14:30:00Z",
      defectForTc5 ? [defectForTc5] : [],
    ),
    buildSeedExecution(
      10,
      2,
      "TC-006",
      "Blocked",
      "JUnit içe aktarım PR'ı bekleniyor.",
      "",
      "tester",
      "2026-11-12T14:35:00Z",
    ),
  ];

  const run3Executions: TestExecution[] = testCases.slice(0, 6).map((tc, index) => {
    const status: ExecutionStatus =
      tc.status === "Passed" || tc.status === "Failed" || tc.status === "Blocked"
        ? tc.status
        : "Not Run";
    return buildSeedExecution(
      20 + index,
      3,
      tc.id,
      status,
      status === "Passed"
        ? "Doğrulama adımları başarıyla tamamlandı."
        : status === "Failed"
          ? "Beklenen sonuç sağlanamadı."
          : "",
      "",
      status === "Not Run" ? null : "tester",
      status === "Not Run" ? null : "2026-11-15T16:00:00Z",
      defects.filter((d) => d.test_case === tc.id).map((d) => d.id),
    );
  });

  return [
    {
      id: 3,
      name: "Sürüm Adayı Doğrulama Koşumu",
      project_id: projectId,
      release_id: releaseId,
      suite_id: 2,
      created_by: "testlead",
      created_at: "2026-11-15T15:45:00Z",
      executions: run3Executions,
    },
    {
      id: 2,
      name: "Sprint 2 Tam Regresyon",
      project_id: projectId,
      release_id: releaseId,
      suite_id: null,
      created_by: "tester",
      created_at: "2026-11-12T14:00:00Z",
      executions: run2Candidates.filter((ex) => tcSet.has(ex.test_case_id)),
    },
    {
      id: 1,
      name: "Sprint 1 Smoke Koşumu",
      project_id: projectId,
      release_id: releaseId,
      suite_id: 1,
      created_by: "tester",
      created_at: "2026-11-10T10:00:00Z",
      executions: run1Candidates.filter((ex) => tcSet.has(ex.test_case_id)),
    },
  ];
}

export function loadPreviewTestRuns(
  projects: Project[],
  releases: Release[],
  testCases: TestCase[],
  defects: Defect[],
): TestRun[] {
  const state = readRunState();
  if (state.runs !== null) {
    return state.runs;
  }
  const seeded = defaultTestRuns(projects, releases, testCases, defects);
  state.runs = seeded;
  writeRunState(state);
  return seeded;
}

export function createPreviewTestRun(
  payload: CreateTestRunPayload,
  username: string,
  projects: Project[],
  releases: Release[],
  testCases: TestCase[],
  defects: Defect[],
): TestRun {
  const state = readRunState();
  const existing = state.runs ?? defaultTestRuns(projects, releases, testCases, defects);
  const runId = state.nextRunId;
  let execId = state.nextExecutionId;

  const executions: TestExecution[] = payload.test_case_ids.map((tcId) => {
    const item: TestExecution = {
      id: execId,
      run_id: runId,
      test_case_id: tcId,
      status: "Not Run",
      actual_result: "",
      notes: "",
      executed_by: null,
      executed_at: null,
      defect_ids: [],
    };
    execId += 1;
    return item;
  });

  const created: TestRun = {
    id: runId,
    name: payload.name.trim(),
    project_id: payload.project_id,
    release_id: payload.release_id,
    suite_id: payload.suite_id,
    created_by: username,
    created_at: new Date().toISOString(),
    executions,
  };

  state.nextRunId = runId + 1;
  state.nextExecutionId = execId;
  state.runs = [created, ...existing];
  writeRunState(state);
  return created;
}

export function recordPreviewExecution(
  runId: number,
  executionId: number,
  payload: RecordExecutionPayload,
  username: string,
): TestExecution | null {
  const state = readRunState();
  if (!state.runs) return null;

  let updatedExec: TestExecution | null = null;
  state.runs = state.runs.map((run) => {
    if (run.id !== runId) return run;
    return {
      ...run,
      executions: run.executions.map((ex) => {
        if (ex.id !== executionId) return ex;
        updatedExec = {
          ...ex,
          status: payload.status,
          actual_result: payload.actual_result.trim(),
          notes: payload.notes.trim(),
          executed_by: username,
          executed_at: new Date().toISOString(),
        };
        return updatedExec;
      }),
    };
  });
  writeRunState(state);
  return updatedExec;
}

export function attachDefectToPreviewExecution(
  runId: number,
  executionId: number,
  defectId: number,
): void {
  const state = readRunState();
  if (!state.runs) return;

  state.runs = state.runs.map((run) => {
    if (run.id !== runId) return run;
    return {
      ...run,
      executions: run.executions.map((ex) => {
        if (ex.id !== executionId) return ex;
        return {
          ...ex,
          defect_ids: Array.from(new Set([...ex.defect_ids, defectId])),
        };
      }),
    };
  });
  writeRunState(state);
}
