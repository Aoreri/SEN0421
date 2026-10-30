import { FormEvent, useEffect, useState } from "react";
import { api, Defect, Metrics, TestCase } from "./api";

const SEVERITIES = ["Low", "Medium", "High", "Critical"];

function Badge({ text }: { text: string }) {
  return <span className={`badge ${text.replace(/\s/g, "-").toLowerCase()}`}>{text}</span>;
}

export default function App() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [tests, setTests] = useState<TestCase[]>([]);
  const [defects, setDefects] = useState<Defect[]>([]);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState("Medium");
  const [error, setError] = useState("");

  async function load() {
    try {
      const [m, t, d] = await Promise.all([api.metrics(), api.testCases(), api.defects()]);
      setMetrics(m);
      setTests(t);
      setDefects(d);
      setError("");
    } catch {
      setError("Backend'e ulaşılamadı. Önce backend'i başlatın (README'ye bakın).");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function addDefect(e: FormEvent) {
    e.preventDefault();
    await api.createDefect(title, severity);
    setTitle("");
    load();
  }

  async function move(id: number, to: string) {
    await api.transition(id, to);
    load();
  }

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
          <table>
            <thead>
              <tr><th>ID</th><th>Başlık</th><th>Gereksinim</th><th>Durum</th></tr>
            </thead>
            <tbody>
              {tests.map((t) => (
                <tr key={t.id}>
                  <td>{t.id}</td>
                  <td>{t.title}</td>
                  <td>{t.requirement}</td>
                  <td><Badge text={t.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section>
          <h2>Defect'ler</h2>
          <form onSubmit={addDefect}>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Yeni defect başlığı"
              required
            />
            <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              {SEVERITIES.map((s) => <option key={s}>{s}</option>)}
            </select>
            <button type="submit">Ekle</button>
          </form>
          <table>
            <thead>
              <tr><th>#</th><th>Başlık</th><th>Önem</th><th>Durum</th><th>Geçiş</th></tr>
            </thead>
            <tbody>
              {defects.map((d) => (
                <tr key={d.id}>
                  <td>{d.id}</td>
                  <td>{d.title}</td>
                  <td>{d.severity}</td>
                  <td><Badge text={d.status} /></td>
                  <td>
                    {d.allowed.map((to) => (
                      <button key={to} onClick={() => move(d.id, to)}>→ {to}</button>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="hint">Yaşam döngüsü: Open → In Progress → Resolved → Closed (+ Reopen)</p>
        </section>

        {error && <p className="error">{error}</p>}
      </main>

      <footer>İstanbul Kültür Üniversitesi · Software Development with Standards · Template v0.1</footer>
    </>
  );
}
