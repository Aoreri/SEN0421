export const SEVERITIES = ["Low", "Medium", "High", "Critical"] as const;
export type Severity = (typeof SEVERITIES)[number];

export const ROLES = ["Admin", "Test Lead", "Tester", "Developer"] as const;
export type Role = (typeof ROLES)[number];

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
};

export type Requirement = {
  id: string;
  project_id: number;
  title: string;
  description: string;
  test_cases: string[];
};

export type TestCase = {
  id: string;
  title: string;
  requirement: string;
  requirements: string[];
  status: string;
};

export type Defect = {
  id: number;
  title: string;
  severity: string;
  status: string;
  test_case: string | null;
  allowed: string[];
};

export type Metrics = {
  total_tests: number;
  execution_rate: number;
  pass_rate: number;
  open_defects: number;
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
  return STATUS_ERROR_MESSAGES[status] ?? (fallbackText || "İstek işlenirken bir hata oluştu.");
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
  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  let res: Response;
  try {
    res = await fetch("/api" + path, {
      headers: {
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      ...options,
    });
  } catch {
    throw new ApiError("Backend'e ulaşılamadı. Önce backend'i başlatın (README'ye bakın).", 0);
  }

  if (!res.ok) {
    if (res.status === 401 && token && path !== "/auth/login") {
      clearStoredToken();
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
    }
    const payload: unknown = await res.json().catch(() => null);
    throw new ApiError(extractErrorDetail(payload, res.status, res.statusText), res.status);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export const api = {
  login: (username: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: username.trim(), password }),
    }),
  me: () => request<User>("/auth/me"),
  metrics: () => request<Metrics>("/metrics"),
  testCases: () => request<TestCase[]>("/test-cases"),
  defects: () => request<Defect[]>("/defects"),
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
};
