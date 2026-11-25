import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatErrorMessage, ImportedTestResult, ImportedTestRun, JUnitImportReport, Project, User } from "../api";
import { DataTable, DataTableColumn } from "../components/DataTable";
import { ErrorAlert } from "../components/ErrorAlert";
import { StatusBadge } from "../components/StatusBadge";

const columns: DataTableColumn<ImportedTestResult>[] = [
  { key: "name", header: "Test", render: r => r.name },
  { key: "case", header: "Eşleşen Vaka", render: r => r.test_case_id ?? "Eşleşmedi" },
  { key: "status", header: "Sonuç", render: r => <StatusBadge text={r.status} /> },
  { key: "defect", header: "Otomatik Defect", render: r => r.defect_id != null
    ? <Link to={`/defects/${r.defect_id}`}>Defect #{r.defect_id}</Link> : "—" },
  { key: "message", header: "Tanı Mesajı", render: r => r.message || "—" },
];

export function ImportResultsTable({ results }: { results: ImportedTestResult[] }) {
  return <DataTable columns={columns} rows={results} getRowKey={r => r.position} ariaLabel="JUnit İçe Aktarım Sonuçları" />;
}

export function JUnitImportsPage({ user }: { user: User | null }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [imports, setImports] = useState<ImportedTestRun[]>([]);
  const [importId, setImportId] = useState<number | null>(null);
  const [report, setReport] = useState<JUnitImportReport | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    setProjects([]); setProjectId(null); setError("");
    if (user) void api.projects().then(rows => {
      if (active) { setProjects(rows); setProjectId(rows[0]?.id ?? null); }
    }).catch(e => { if (active) setError(formatErrorMessage(e, "Projeler yüklenemedi")); });
    return () => { active = false; };
  }, [user]);

  useEffect(() => {
    let active = true;
    setImports([]); setImportId(null); setReport(null); setError("");
    if (user && projectId !== null) void api.junitImports(projectId, 50).then(rows => {
      if (active) { setImports(rows); setImportId(rows[0]?.id ?? null); }
    }).catch(e => { if (active) setError(formatErrorMessage(e, "Raporlar yüklenemedi")); });
    return () => { active = false; };
  }, [user, projectId]);

  useEffect(() => {
    let active = true;
    setReport(null); setLoading(false); setError("");
    if (user && projectId !== null && importId !== null) {
      setLoading(true);
      void api.junitImport(projectId, importId).then(row => { if (active) setReport(row); })
        .catch(e => { if (active) setError(formatErrorMessage(e, "Rapor yüklenemedi")); })
        .finally(() => { if (active) setLoading(false); });
    }
    return () => { active = false; };
  }, [user, projectId, importId]);

  if (!user) return <section><h2>JUnit İçe Aktarım Raporları</h2><p>Raporları görmek için <Link to="/login">giriş yapın</Link>.</p></section>;
  return <section>
    <h2>JUnit İçe Aktarım Raporları</h2>
    <p>Seçilen projenin son 50 içe aktarımı. Başarısız sonuçtan açılan veya yeniden kullanılan defect bağlantısı raporda korunur.</p>
    <ErrorAlert message={error} />
    <label htmlFor="import-project">Proje</label>
    <select id="import-project" value={projectId ?? ""} onChange={e => setProjectId(Number(e.target.value))}>
      {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
    </select>
    <label htmlFor="import-report">İçe Aktarım</label>
    <select id="import-report" value={importId ?? ""} onChange={e => setImportId(Number(e.target.value))} disabled={!imports.length}>
      {imports.map(r => <option key={r.id} value={r.id}>#{r.id} · {r.created_at} · {r.summary.total} sonuç</option>)}
    </select>
    {!imports.length && <p>Bu projede içe aktarım raporu bulunamadı.</p>}
    {loading && <p role="status">Rapor yükleniyor...</p>}
    {report && <><p>Toplam: {report.summary.total} · Eşleşen: {report.summary.matched} · Eşleşmeyen: {report.summary.unmatched}</p><ImportResultsTable results={report.results} /></>}
  </section>;
}
