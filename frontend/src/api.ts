export const SEVERITIES = ["Low", "Medium", "High", "Critical"] as const;
export type Severity = (typeof SEVERITIES)[number];

export type TestCase = {
  id: string;
  title: string;
  requirement: string;
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

const STATUS_ERROR_MESSAGES: Record<number, string> = {
  400: "Geçersiz istek gönderildi.",
  404: "İstenen kayıt bulunamadı.",
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
  let res: Response;
  try {
    res = await fetch("/api" + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError("Backend'e ulaşılamadı. Önce backend'i başlatın (README'ye bakın).", 0);
  }

  if (!res.ok) {
    const payload: unknown = await res.json().catch(() => null);
    throw new ApiError(extractErrorDetail(payload, res.status, res.statusText), res.status);
  }
  return res.json();
}

export const api = {
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
};

