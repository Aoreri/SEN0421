import { translate } from "./i18nTranslate";

export const SEVERITIES = ["Low", "Medium", "High", "Critical"] as const;
export type Severity = (typeof SEVERITIES)[number];

export const PRIORITIES = ["Low", "Medium", "High", "Critical"] as const;
export type Priority = (typeof PRIORITIES)[number];

export const TEST_PRIORITIES = PRIORITIES;
export type TestPriority = Priority;

export const TEST_CASE_STATUSES = [
  "Not Run",
  "Passed",
  "Failed",
  "Blocked",
  "Skipped",
] as const;
export type TestCaseStatus = (typeof TEST_CASE_STATUSES)[number];

export const EXECUTION_STATUSES = TEST_CASE_STATUSES;
export type ExecutionStatus = TestCaseStatus;

export const RECORDABLE_EXECUTION_STATUSES = [
  "Passed",
  "Failed",
  "Blocked",
  "Skipped",
] as const;
export type RecordableExecutionStatus = (typeof RECORDABLE_EXECUTION_STATUSES)[number];

export const ROLES = ["Admin", "Test Lead", "Tester", "Developer"] as const;
export type Role = (typeof ROLES)[number];

export const RELEASE_STATUSES = ["Planned", "In Test", "Ready", "Released"] as const;
export type ReleaseStatus = (typeof RELEASE_STATUSES)[number];

export const SPRINT_STATUSES = ["Planned", "Active", "Completed"] as const;
export type SprintStatus = (typeof SPRINT_STATUSES)[number];

export type User = {
  id: number;
  username: string;
  role: Role;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type Project = {
  id: number;
  name: string;
  description: string;
};

export type Release = {
  id: number;
  project_id: number;
  version: string;
  status: ReleaseStatus;
};

export type Sprint = {
  id: number;
  project_id: number;
  release_id: number | null;
  name: string;
  goal: string;
  start_at: string | null;
  end_at: string | null;
  status: SprintStatus;
};

export type SprintInput = {
  project_id: number;
  release_id?: number | null;
  name: string;
  goal?: string;
  start_at?: string | null;
  end_at?: string | null;
  status?: SprintStatus;
};

export type Requirement = {
  id: string;
  project_id: number;
  title: string;
  description: string;
  test_cases: string[];
};

export type TestSuite = {
  id: number;
  project_id: number;
  name: string;
  description: string;
  test_cases: string[];
};

export type TestCase = {
  id: string;
  suite_id: number | null;
  title: string;
  requirement: string;
  requirements: string[];
  status: string;
  priority: Priority;
  automated: boolean;
  steps: string[];
  expected_result: string;
  stable_key?: string;
};

export type TestCaseInput = {
  title: string;
  suite_id?: number | null;
  priority?: Priority;
  automated?: boolean;
  steps?: string[];
  expected_result?: string;
  status?: TestCaseStatus;
  requirements: string[];
};

export type TestCaseCreateInput = TestCaseInput & {
  id: string;
};

export type TestSuitePayload = {
  project_id: number;
  name: string;
  description: string;
  test_cases?: string[];
};

export type TestExecution = {
  id: number;
  run_id: number;
  test_case_id: string;
  status: ExecutionStatus;
  actual_result: string;
  notes: string;
  executed_by: string | null;
  executed_at: string | null;
  defect_ids: number[];
};

export type TestRun = {
  id: number;
  name: string;
  project_id: number;
  release_id: number | null;
  sprint_id?: number | null;
  suite_id: number | null;
  created_by: string;
  created_at: string;
  executions: TestExecution[];
};

export type CreateTestRunPayload = {
  name: string;
  project_id: number;
  release_id: number | null;
  sprint_id?: number | null;
  suite_id: number | null;
  test_case_ids: string[];
};

export type RecordExecutionPayload = {
  status: RecordableExecutionStatus;
  actual_result: string;
  notes: string;
  defect_ids?: number[];
};

export type Defect = {
  id: number;
  title: string;
  severity: string;
  status: string;
  test_case: string | null;
  allowed: string[];
};

export type DefectHistoryEntry = {
  defect_id: number;
  from: string | null;
  to: string;
  at: string;
};

export type Metrics = {
  total_tests: number;
  execution_rate: number;
  pass_rate: number;
  open_defects: number;
};

export type ImportedTestResult = {
  position: number;
  name: string;
  classname: string;
  suite: string;
  reported_key: string;
  test_case_id: string | null;
  status: "Passed" | "Failed" | "Skipped";
  duration_seconds: number | null;
  message: string;
  unmatched_reason: "unknown_test_case" | "not_linked_to_project" | null;
  failure_signature: string | null;
  defect_id: number | null;
};

export type ImportedTestRun = {
  id: number;
  project_id: number;
  imported_by: number;
  commit: string | null;
  branch: string | null;
  created_at: string;
  summary: {
    total: number; matched: number; unmatched: number;
    passed: number; failed: number; skipped: number;
  };
};

export type JUnitImportReport = ImportedTestRun & {
  results: ImportedTestResult[];
  unmatched_results: ImportedTestResult[];
};

export type RunMetricPoint = {
  run_id: number;
  run_name: string;
  executed_at: string; // ISO-8601 with an explicit UTC offset on both database backends.
  passed: number;
  failed: number;
  blocked: number;
  skipped: number;
  not_run: number;
  pass_rate: number;
};

export type DefectBurnupPoint = {
  date: string;
  opened: number;
  closed: number;
  open_remaining: number;
};

export type SeverityDistributionItem = {
  severity: Severity;
  total: number;
  open: number;
  closed: number;
};

export type ExpandedMetrics = Metrics & {
  requirement_coverage: number;
  reopen_rate: number;
  avg_defect_age_hours: number | null;
  avg_resolution_hours: number | null;
  run_series: RunMetricPoint[];
  defect_burnup: DefectBurnupPoint[];
  severity_distribution: SeverityDistributionItem[];
};

export type ExitCriteriaConfig = {
  min_pass_rate: number;
  max_open_critical: number;
  min_req_coverage: number;
};

export type ReleaseWaiver = {
  waived_by: string;
  reason: string;
  waived_at: string;
};

export type ReleaseGateStatus = {
  release_id: number;
  release_version: string;
  status: ReleaseStatus;
  criteria: ExitCriteriaConfig;
  actual_pass_rate: number;
  actual_open_critical: number;
  actual_req_coverage: number;
  passed_criteria: {
    pass_rate: boolean;
    open_critical: boolean;
    req_coverage: boolean;
  };
  gate_passed: boolean;
  waiver: ReleaseWaiver | null;
};

export const TEST_PLAN_STATUSES = ["Draft", "In Review", "Approved"] as const;
export type TestPlanStatus = (typeof TEST_PLAN_STATUSES)[number];

export type TestPlanSnapshotSummary = {
  id: number;
  test_plan_id: number;
  version: string;
  status: TestPlanStatus;
  generated_by: string;
  generated_at: string;
};

export type TestPlanSnapshot = TestPlanSnapshotSummary & {
  html_content: string;
  payload: Record<string, unknown>;
};

export type TestPlan = {
  id: number;
  project_id: number;
  release_id: number | null;
  version: string;
  title: string;
  status: TestPlanStatus;
  scope: string;
  approach: string;
  pass_fail_criteria: string;
  environment: string;
  schedule_risks: string;
  created_by: string;
  created_at: string;
  snapshot_count: number;
  snapshots?: TestPlanSnapshotSummary[];
};

export type TestPlanInput = {
  project_id: number;
  release_id?: number | null;
  version: string;
  title: string;
  scope?: string;
  approach?: string;
  pass_fail_criteria?: string;
  environment?: string;
  schedule_risks?: string;
};

export type TestSummaryReportSnapshotSummary = {
  id: number;
  release_id: number;
  release_version: string;
  release_status: ReleaseStatus;
  gate_passed: boolean;
  generated_by: string;
  generated_at: string;
};

export type TestSummaryReportSnapshot = TestSummaryReportSnapshotSummary & {
  html_content: string;
  payload: Record<string, unknown>;
};

export type TestIncidentReportSnapshotSummary = {
  id: number;
  defect_id: number;
  status: string;
  severity: string;
  generated_by: string;
  generated_at: string;
};

export type TestIncidentReportSnapshot = TestIncidentReportSnapshotSummary & {
  html_content: string;
  payload: Record<string, unknown>;
};

export type TestLogSnapshotSummary = {
  id: number;
  test_run_id: number;
  generated_by: string;
  generated_at: string;
};

export type TestLogSnapshot = TestLogSnapshotSummary & {
  html_content: string;
  payload: Record<string, unknown>;
};

const TOKEN_STORAGE_KEY = "token";
export const AUTH_EXPIRED_EVENT = "sds06:auth-expired";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

const STATUS_ERROR_MESSAGES: Record<number, string> = {
  400: "Geçersiz istek gönderildi.",
  401: "Oturum süresi doldu veya kimlik doğrulama gerekli.",
  403: "Bu işlem için yetkiniz yok.",
  404: "İstenen kayıt bulunamadı.",
  409: "Kayıt başka verilerle veya durum kurallarıyla çakışıyor.",
  422: "Gönderilen form verileri doğrulamadan geçemedi.",
  500: "Sunucu hatası oluştu. Lütfen daha sonra tekrar deneyin.",
  502: "Backend servisine ulaşılamadı. Önce backend'i başlatın (README'ye bakın).",
  503: "Servis şu anda kullanılamıyor.",
};

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function isEndpointUnavailableError(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    (error.status === 404 || error.status === 405 || error.status === 501)
  );
}

function extractErrorDetail(payload: unknown, status: number, fallbackText: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const { detail } = payload as { detail: unknown };
    if (typeof detail === "string" && detail.trim()) {
      return detail.trim();
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item && typeof item.msg === "string"
            ? item.msg
            : null,
        )
        .filter((msg): msg is string => Boolean(msg));
      if (messages.length > 0) {
        return messages.join(" ");
      }
    }
  }
  return (
    translate(STATUS_ERROR_MESSAGES[status] ?? (fallbackText || "İstek işlenirken bir hata oluştu."))
  );
}

export function formatErrorMessage(
  error: unknown,
  fallback = "İşlem sırasında beklenmeyen bir hata oluştu.",
): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim();
  }
  return translate(fallback);
}

async function send(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getStoredToken();
  let res: Response;
  try {
    res = await fetch("/api" + path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(
      translate("Backend'e ulaşılamadı. Önce backend'i başlatın (README'ye bakın)."),
      0,
    );
  }

  if (!res.ok) {
    if (res.status === 401 && token && path !== "/auth/login") {
      clearStoredToken();
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
    }
    const payload: unknown = await res.json().catch(() => null);
    throw new ApiError(extractErrorDetail(payload, res.status, res.statusText), res.status);
  }
  return res;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await send(path, options);

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export type CoverageSummary = {
  lines_valid: number; lines_covered: number;
  branches_valid: number; branches_covered: number;
  line_coverage: number; branch_coverage: number;
};
export type CoverageImport = {
  id: number; project_id: number; imported_by: number;
  junit_import_id: number | null; commit: string | null;
  branch: string | null; created_at: string; summary: CoverageSummary;
};
export type CoverageReport = CoverageImport & {
  files: (CoverageSummary & { filename: string })[];
};

/** Bearer token ile indirir; düz `<a href>` gezinmesi Authorization başlığını göndermez. */
async function download(path: string, fallbackName: string): Promise<void> {
  const res = await send(path);
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? fallbackName;
  const url = URL.createObjectURL(await res.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export const api = {
  login: (username: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: username.trim(), password }),
    }),
  me: () => request<User>("/auth/me"),
  metrics: () => request<Metrics>("/metrics"),
  expandedMetrics: (
    releaseId?: number | null,
    options: {
      projectId?: number | null;
      sprintId?: number | null;
      startAt?: string | null;
      endAt?: string | null;
    } = {},
  ) => {
    const params = new URLSearchParams();
    if (options.projectId) params.set("project_id", String(options.projectId));
    if (releaseId) params.set("release_id", String(releaseId));
    if (options.sprintId) params.set("sprint_id", String(options.sprintId));
    if (options.startAt) params.set("start_at", options.startAt);
    if (options.endAt) params.set("end_at", options.endAt);
    const qs = params.toString();
    return request<ExpandedMetrics>(qs ? `/metrics/expanded?${qs}` : "/metrics/expanded");
  },
  testSuites: () => request<TestSuite[]>("/test-suites"),
  getTestSuite: (id: number) => request<TestSuite>(`/test-suites/${id}`),
  createTestSuite: (project_id: number, name: string, description = "") =>
    request<TestSuite>("/test-suites", {
      method: "POST",
      body: JSON.stringify({
        project_id,
        name: name.trim(),
        description: description.trim(),
      }),
    }),
  updateTestSuite: (id: number, project_id: number, name: string, description = "") =>
    request<TestSuite>(`/test-suites/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        project_id,
        name: name.trim(),
        description: description.trim(),
      }),
    }),
  deleteTestSuite: (id: number) => request<void>(`/test-suites/${id}`, { method: "DELETE" }),
  testCases: () => request<TestCase[]>("/test-cases"),
  getTestCase: (id: string) =>
    request<TestCase>(`/test-cases/${encodeURIComponent(id)}`),
  createTestCase: (input: TestCaseCreateInput) =>
    request<TestCase>("/test-cases", {
      method: "POST",
      body: JSON.stringify({
        ...input,
        id: input.id.trim(),
        title: input.title.trim(),
        expected_result: (input.expected_result ?? "").trim(),
      }),
    }),
  updateTestCase: (id: string, input: TestCaseInput) =>
    request<TestCase>(`/test-cases/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify({
        ...input,
        title: input.title.trim(),
        expected_result: (input.expected_result ?? "").trim(),
      }),
    }),
  deleteTestCase: (id: string) =>
    request<void>(`/test-cases/${encodeURIComponent(id)}`, { method: "DELETE" }),
  setTestCaseRequirements: (id: string, requirements: string[]) =>
    request<TestCase>(`/test-cases/${encodeURIComponent(id)}/requirements`, {
      method: "PUT",
      body: JSON.stringify({ requirements }),
    }),
  testRuns: () => request<TestRun[]>("/test-runs"),
  getTestRun: (id: number) => request<TestRun>(`/test-runs/${id}`),
  createTestRun: (payload: CreateTestRunPayload) =>
    request<TestRun>("/test-runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  recordExecution: (runId: number, executionId: number, payload: RecordExecutionPayload) =>
    request<TestExecution>(`/test-runs/${runId}/executions/${executionId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createDefectFromExecution: (
    runId: number,
    executionId: number,
    payload: { title: string; severity: string },
  ) =>
    request<Defect>(`/test-runs/${runId}/executions/${executionId}/defects`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  defects: () => request<Defect[]>("/defects"),
  defectHistory: (id: number) => request<DefectHistoryEntry[]>(`/defects/${id}/history`),
  createDefect: (title: string, severity: string, test_case: string | null = null) =>
    request<Defect>("/defects", {
      method: "POST",
      body: JSON.stringify({ title: title.trim(), severity, test_case }),
    }),
  transition: (id: number, to: string) =>
    request<Defect>(`/defects/${id}/transition`, { method: "POST", body: JSON.stringify({ to }) }),
  projects: () => request<Project[]>("/projects"),
  createProject: (name: string, description = "") =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ name: name.trim(), description: description.trim() }),
    }),
  updateProject: (id: number, name: string, description = "") =>
    request<Project>(`/projects/${id}`, {
      method: "PUT",
      body: JSON.stringify({ name: name.trim(), description: description.trim() }),
    }),
  deleteProject: (id: number) => request<void>(`/projects/${id}`, { method: "DELETE" }),
  releases: () => request<Release[]>("/releases"),
  createRelease: (project_id: number, version: string) =>
    request<Release>("/releases", {
      method: "POST",
      body: JSON.stringify({ project_id, version: version.trim() }),
    }),
  updateRelease: (id: number, project_id: number, version: string) =>
    request<Release>(`/releases/${id}`, {
      method: "PUT",
      body: JSON.stringify({ project_id, version: version.trim() }),
    }),
  deleteRelease: (id: number) => request<void>(`/releases/${id}`, { method: "DELETE" }),
  sprints: (filters: { projectId?: number | null; releaseId?: number | null } = {}) => {
    const params = new URLSearchParams();
    if (filters.projectId) params.set("project_id", String(filters.projectId));
    if (filters.releaseId) params.set("release_id", String(filters.releaseId));
    const qs = params.toString();
    return request<Sprint[]>(qs ? `/sprints?${qs}` : "/sprints");
  },
  getSprint: (id: number) => request<Sprint>(`/sprints/${id}`),
  createSprint: (input: SprintInput) =>
    request<Sprint>("/sprints", {
      method: "POST",
      body: JSON.stringify({
        ...input,
        name: input.name.trim(),
        goal: (input.goal ?? "").trim(),
      }),
    }),
  updateSprint: (id: number, input: SprintInput) =>
    request<Sprint>(`/sprints/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        ...input,
        name: input.name.trim(),
        goal: (input.goal ?? "").trim(),
      }),
    }),
  deleteSprint: (id: number) => request<void>(`/sprints/${id}`, { method: "DELETE" }),
  releaseGate: (releaseId: number) => request<ReleaseGateStatus>(`/releases/${releaseId}/gate`),
  updateReleaseStatus: (releaseId: number, status: ReleaseStatus) =>
    request<ReleaseGateStatus>(`/releases/${releaseId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }),
  updateExitCriteria: (releaseId: number, criteria: ExitCriteriaConfig) =>
    request<ReleaseGateStatus>(`/releases/${releaseId}/criteria`, {
      method: "PUT",
      body: JSON.stringify(criteria),
    }),
  createReleaseWaiver: (releaseId: number, reason: string) =>
    request<ReleaseGateStatus>(`/releases/${releaseId}/waiver`, {
      method: "POST",
      body: JSON.stringify({ reason: reason.trim() }),
    }),
  deleteReleaseWaiver: (releaseId: number) =>
    request<ReleaseGateStatus>(`/releases/${releaseId}/waiver`, {
      method: "DELETE",
    }),
  requirements: () => request<Requirement[]>("/requirements"),
  createRequirement: (id: string, project_id: number, title: string, description = "") =>
    request<Requirement>("/requirements", {
      method: "POST",
      body: JSON.stringify({
        id: id.trim(),
        project_id,
        title: title.trim(),
        description: description.trim(),
      }),
    }),
  updateRequirement: (id: string, project_id: number, title: string, description = "") =>
    request<Requirement>(`/requirements/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify({
        project_id,
        title: title.trim(),
        description: description.trim(),
      }),
    }),
  deleteRequirement: (id: string) =>
    request<void>(`/requirements/${encodeURIComponent(id)}`, { method: "DELETE" }),
  setRequirementTestCases: (id: string, test_cases: string[]) =>
    request<Requirement>(`/requirements/${encodeURIComponent(id)}/test-cases`, {
      method: "PUT",
      body: JSON.stringify({ test_cases }),
    }),
  importJUnit: (projectId: number, xml: string, metadata: { commit?: string; branch?: string } = {}) => {
    const query = new URLSearchParams(
      Object.entries(metadata).filter((entry): entry is [string, string] => entry[1] !== undefined),
    ).toString();
    return request<JUnitImportReport>(`/projects/${projectId}/runs/import${query ? `?${query}` : ""}`, {
      method: "POST",
      headers: { "Content-Type": "application/xml" },
      body: xml,
    });
  },
  importCoverage: (projectId: number, xml: string,
    metadata: { commit?: string; branch?: string; junit_import_id?: number } = {}) => {
    const query = new URLSearchParams();
    Object.entries(metadata).forEach(([key, value]) => {
      if (value !== undefined) query.set(key, String(value));
    });
    return request<CoverageReport>(`/projects/${projectId}/coverage/import${query.size ? `?${query}` : ""}`, {
      method: "POST", headers: { "Content-Type": "application/xml" }, body: xml,
    });
  },
  coverageImports: (projectId: number, limit = 50, offset = 0) =>
    request<CoverageImport[]>(`/projects/${projectId}/coverage/imports?limit=${limit}&offset=${offset}`),
  coverageImport: (projectId: number, importId: number) =>
    request<CoverageReport>(`/projects/${projectId}/coverage/imports/${importId}`),
  junitImports: (projectId: number, limit = 50, offset = 0) =>
    request<ImportedTestRun[]>(`/projects/${projectId}/runs/imports?limit=${limit}&offset=${offset}`),
  junitImport: (projectId: number, importId: number) =>
    request<JUnitImportReport>(`/projects/${projectId}/runs/imports/${importId}`),
  testPlans: () => request<TestPlan[]>("/test-plans"),
  getTestPlan: (id: number) => request<TestPlan>(`/test-plans/${id}`),
  createTestPlan: (input: TestPlanInput) =>
    request<TestPlan>("/test-plans", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateTestPlan: (id: number, input: TestPlanInput) =>
    request<TestPlan>(`/test-plans/${id}`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  updateTestPlanStatus: (id: number, status: TestPlanStatus) =>
    request<TestPlan>(`/test-plans/${id}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }),
  deleteTestPlan: (id: number) =>
    request<void>(`/test-plans/${id}`, { method: "DELETE" }),
  createTestPlanSnapshot: (id: number) =>
    request<TestPlanSnapshot>(`/test-plans/${id}/snapshots`, { method: "POST" }),
  getTestPlanSnapshot: (planId: number, snapshotId: number) =>
    request<TestPlanSnapshot>(`/test-plans/${planId}/snapshots/${snapshotId}`),
  summaryReportSnapshots: (releaseId: number) =>
    request<TestSummaryReportSnapshotSummary[]>(
      `/releases/${releaseId}/summary-report/snapshots`,
    ),
  createSummaryReportSnapshot: (releaseId: number) =>
    request<TestSummaryReportSnapshot>(`/releases/${releaseId}/summary-report/snapshots`, {
      method: "POST",
    }),
  getSummaryReportSnapshot: (releaseId: number, snapshotId: number) =>
    request<TestSummaryReportSnapshot>(
      `/releases/${releaseId}/summary-report/snapshots/${snapshotId}`,
    ),
  downloadSummaryReport: (releaseId: number, format: "html" | "pdf", snapshotId?: number) =>
    download(
      `/releases/${releaseId}/summary-report/export?format=${format}${
        snapshotId !== undefined ? `&snapshot_id=${snapshotId}` : ""
      }`,
      `test-summary-report-${releaseId}${snapshotId !== undefined ? `-snap-${snapshotId}` : ""}.${format}`,
    ),
  downloadTestPlan: (planId: number, format: "html" | "pdf", snapshotId?: number) =>
    download(
      `/test-plans/${planId}/export?format=${format}${
        snapshotId !== undefined ? `&snapshot_id=${snapshotId}` : ""
      }`,
      `test-plan-${planId}${snapshotId !== undefined ? `-snap-${snapshotId}` : ""}.${format}`,
    ),
  incidentReportSnapshots: (defectId: number) =>
    request<TestIncidentReportSnapshotSummary[]>(`/defects/${defectId}/incident-report/snapshots`),
  createIncidentReportSnapshot: (defectId: number) =>
    request<TestIncidentReportSnapshot>(`/defects/${defectId}/incident-report/snapshots`, {
      method: "POST",
    }),
  getIncidentReportSnapshot: (defectId: number, snapshotId: number) =>
    request<TestIncidentReportSnapshot>(
      `/defects/${defectId}/incident-report/snapshots/${snapshotId}`,
    ),
  downloadIncidentReport: (defectId: number, format: "html" | "pdf", snapshotId?: number) =>
    download(
      `/defects/${defectId}/incident-report/export?format=${format}${
        snapshotId !== undefined ? `&snapshot_id=${snapshotId}` : ""
      }`,
      `test-incident-report-${defectId}${snapshotId !== undefined ? `-snap-${snapshotId}` : ""}.${format}`,
    ),
  testLogSnapshots: (runId: number) =>
    request<TestLogSnapshotSummary[]>(`/test-runs/${runId}/test-log/snapshots`),
  createTestLogSnapshot: (runId: number) =>
    request<TestLogSnapshot>(`/test-runs/${runId}/test-log/snapshots`, {
      method: "POST",
    }),
  getTestLogSnapshot: (runId: number, snapshotId: number) =>
    request<TestLogSnapshot>(`/test-runs/${runId}/test-log/snapshots/${snapshotId}`),
  downloadTestLog: (runId: number, format: "html" | "pdf", snapshotId?: number) =>
    download(
      `/test-runs/${runId}/test-log/export?format=${format}${
        snapshotId !== undefined ? `&snapshot_id=${snapshotId}` : ""
      }`,
      `test-log-${runId}${snapshotId !== undefined ? `-snap-${snapshotId}` : ""}.${format}`,
    ),
};
