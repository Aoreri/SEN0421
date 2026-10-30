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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
  return res.json();
}

export const api = {
  metrics: () => request<Metrics>("/metrics"),
  testCases: () => request<TestCase[]>("/test-cases"),
  defects: () => request<Defect[]>("/defects"),
  createDefect: (title: string, severity: string) =>
    request<Defect>("/defects", { method: "POST", body: JSON.stringify({ title, severity }) }),
  transition: (id: number, to: string) =>
    request<Defect>(`/defects/${id}/transition`, { method: "POST", body: JSON.stringify({ to }) }),
};
