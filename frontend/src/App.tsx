import { FormEvent, useEffect, useState } from "react";
import { api, Defect, formatErrorMessage, Metrics, SEVERITIES, TestCase } from "./api";
import { DataTable, DataTableColumn } from "./components/DataTable";
import { ErrorAlert } from "./components/ErrorAlert";
import { FormField } from "./components/FormField";
import { StatusBadge } from "./components/StatusBadge";
import { DefectFormErrors, hasFormErrors, validateDefectForm } from "./validation";

const TEST_CASE_COLUMNS: DataTableColumn<TestCase>[] = [
  { key: "id", header: "ID", render: (t) => t.id },
  { key: "title", header: "Başlık", render: (t) => t.title },
  { key: "requirement", header: "Gereksinim", render: (t) => t.requirement },
  { key: "status", header: "Durum", render: (t) => <StatusBadge text={t.status} /> },
];

export default function App() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [tests, setTests] = useState<TestCase[]>([]);
  const [defects, setDefects] = useState<Defect[]>([]);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState("Medium");
  const [testCase, setTestCase] = useState("");
  const [formErrors, setFormErrors] = useState<DefectFormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [transitioningId, setTransitioningId] = useState<number | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      const [m, t, d] = await Promise.all([api.metrics(), api.testCases(), api.defects()]);
      setMetrics(m);
      setTests(t);
      setDefects(d);
      setError("");
    } catch (err) {
      setError(
        formatErrorMessage(
          err,
          "Backend'e ulaşılamadı. Önce backend'i başlatın (README'ye bakın).",
        ),
      );
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function addDefect(e: FormEvent) {
    e.preventDefault();
    const validationErrors = validateDefectForm(
      { title, severity, testCase },
      tests.map((t) => t.id),
    );
    setFormErrors(validationErrors);
    if (hasFormErrors(validationErrors)) {
      return;
    }

    setSubmitting(true);
    try {
      await api.createDefect(title, severity, testCase || null);
      setTitle("");
      setTestCase("");
      setFormErrors({});
      setError("");
      await load();
    } catch (err) {
      setError(formatErrorMessage(err, "Defect oluşturulurken bir hata oluştu."));
    } finally {
      setSubmitting(false);
    }
  }

  async function move(id: number, to: string) {
    setTransitioningId(id);
    try {
      await api.transition(id, to);
      setError("");
      await load();
    } catch (err) {
      setError(formatErrorMessage(err, "Durum geçişi sırasında bir hata oluştu."));
    } finally {
      setTransitioningId(null);
    }
  }

  const defectColumns: DataTableColumn<Defect>[] = [
    { key: "id", header: "#", render: (d) => d.id },
    { key: "title", header: "Başlık", render: (d) => d.title },
    { key: "test_case", header: "Test Vakası", render: (d) => d.test_case ?? "—" },
    { key: "severity", header: "Önem", render: (d) => <StatusBadge text={d.severity} /> },
    { key: "status", header: "Durum", render: (d) => <StatusBadge text={d.status} /> },
    {
      key: "allowed",
      header: "Geçiş",
      render: (d) =>
        d.allowed.map((to) => (
          <button
            key={to}
            type="button"
            disabled={transitioningId === d.id}
            onClick={() => move(d.id, to)}
          >
            → {to}
          </button>
        )),
    },
  ];

  return (
    <>
      <div className="banner">
        ⚠️ Bu bir <strong>DEMO / TEMPLATE</strong> sitesidir. Veriler örnektir ve sunucu yeniden
        başlatıldığında sıfırlanır.
      </div>

      <header>
        <h1>SDS-06 · Agile Test and Defect Tracking System</h1>
        <p>ISO/IEC/IEEE 12207 · IEEE 829 · ISO/IEC/IEEE 29119-2 / 29119-3</p>
      </header>

      <main>
        <ErrorAlert message={error} onDismiss={() => setError("")} />

        {metrics && (
          <section className="metrics">
            {[
              ["Toplam Test", metrics.total_tests],
              ["Koşum Oranı", `${metrics.execution_rate}%`],
              ["Başarı Oranı", `${metrics.pass_rate}%`],
              ["Açık Defect", metrics.open_defects],
            ].map(([label, value]) => (
              <div className="card" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </section>
        )}

        <section>
          <h2>Test Vakaları</h2>
          <DataTable
            columns={TEST_CASE_COLUMNS}
            rows={tests}
            getRowKey={(t) => t.id}
            emptyMessage="Kayıtlı test vakası bulunamadı."
            ariaLabel="Test Vakaları"
          />
        </section>

        <section>
          <h2>Defect&apos;ler</h2>
          <form onSubmit={addDefect} noValidate>
            <FormField id="defect-title" label="Başlık" required error={formErrors.title}>
              <input
                id="defect-title"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  if (formErrors.title) {
                    setFormErrors((prev) => ({ ...prev, title: undefined }));
                  }
                }}
                placeholder="Yeni defect başlığı (en az 3 karakter)"
                aria-invalid={Boolean(formErrors.title)}
                aria-describedby={formErrors.title ? "defect-title-error" : undefined}
              />
            </FormField>

            <FormField id="defect-severity" label="Önem" required error={formErrors.severity}>
              <select
                id="defect-severity"
                value={severity}
                onChange={(e) => {
                  setSeverity(e.target.value);
                  if (formErrors.severity) {
                    setFormErrors((prev) => ({ ...prev, severity: undefined }));
                  }
                }}
                aria-invalid={Boolean(formErrors.severity)}
                aria-describedby={formErrors.severity ? "defect-severity-error" : undefined}
              >
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField id="defect-test-case" label="Test Vakası" error={formErrors.testCase}>
              <select
                id="defect-test-case"
                value={testCase}
                onChange={(e) => {
                  setTestCase(e.target.value);
                  if (formErrors.testCase) {
                    setFormErrors((prev) => ({ ...prev, testCase: undefined }));
                  }
                }}
                aria-invalid={Boolean(formErrors.testCase)}
                aria-describedby={formErrors.testCase ? "defect-test-case-error" : undefined}
              >
                <option value="">Bağlı değil</option>
                {tests.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.id} · {t.title}
                  </option>
                ))}
              </select>
            </FormField>

            <div className="form-actions">
              <button type="submit" disabled={submitting}>
                {submitting ? "Ekleniyor..." : "Ekle"}
              </button>
            </div>
          </form>

          <DataTable
            columns={defectColumns}
            rows={defects}
            getRowKey={(d) => d.id}
            emptyMessage="Kayıtlı defect bulunamadı."
            ariaLabel="Defect Listesi"
          />
          <p className="hint">Yaşam döngüsü: Open → In Progress → Resolved → Closed (+ Reopen)</p>
        </section>
      </main>

      <footer>
        İstanbul Kültür Üniversitesi · Software Development with Standards · Template v0.1
      </footer>
    </>
  );
}

