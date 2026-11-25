import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  api,
  ExitCriteriaConfig,
  ExpandedMetrics,
  formatErrorMessage,
  Project,
  Release,
  ReleaseGateStatus,
  ReleaseStatus,
  Sprint,
  TestSummaryReportSnapshotSummary,
  User,
} from "../api";
import { DataTable, DataTableColumn } from "../components/DataTable";
import { ErrorAlert } from "../components/ErrorAlert";
import { MetricsCharts } from "../components/MetricsCharts";
import { ReleaseGateCard } from "../components/ReleaseGateCard";
import { StatusBadge } from "../components/StatusBadge";

export type ReleasesPageProps = {
  user: User | null;
};

export function ReleasesPage({ user }: ReleasesPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const releaseParam = Number(searchParams.get("release")) || null;

  const [projects, setProjects] = useState<Project[]>([]);
  const [releases, setReleases] = useState<Release[]>([]);
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [sprintChoice, setSprintChoice] = useState<{ releaseId: number; sprintId: number } | null>(
    null,
  );
  const [gate, setGate] = useState<ReleaseGateStatus | null>(null);
  const [metrics, setMetrics] = useState<ExpandedMetrics | null>(null);
  const [snapshots, setSnapshots] = useState<TestSummaryReportSnapshotSummary[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const releaseId =
    releaseParam && releases.some((r) => r.id === releaseParam)
      ? releaseParam
      : (releases[0]?.id ?? null);

  // Sprint seçimi kendi sürümüne bağlıdır; sürüm değişince filtre kendiliğinden düşer.
  const sprintId = sprintChoice?.releaseId === releaseId ? sprintChoice.sprintId : null;

  const canCreateSnapshot =
    user !== null &&
    (user.role === "Admin" || user.role === "Test Lead" || user.role === "Tester");

  useEffect(() => {
    Promise.all([api.projects(), api.releases()])
      .then(([p, r]) => {
        setProjects(p);
        setReleases(r);
      })
      .catch((err) => setError(formatErrorMessage(err, "Sürümler yüklenemedi.")));
  }, [user]);

  useEffect(() => {
    setSprints([]);
    if (releaseId === null) return;
    api
      .sprints({ releaseId })
      .then(setSprints)
      .catch((err) => setError(formatErrorMessage(err, "Sprintler yüklenemedi.")));
  }, [releaseId]);

  const loadRelease = useCallback(async () => {
    if (releaseId === null) {
      setGate(null);
      setMetrics(null);
      setSnapshots([]);
      return;
    }
    try {
      const [g, m, s] = await Promise.all([
        api.releaseGate(releaseId),
        api.expandedMetrics(releaseId, { sprintId }),
        api.summaryReportSnapshots(releaseId),
      ]);
      setGate(g);
      setMetrics(m);
      setSnapshots(s);
      setError("");
    } catch (err) {
      setError(formatErrorMessage(err, "Sürüm verileri yüklenemedi."));
    }
  }, [releaseId, sprintId]);

  useEffect(() => {
    void loadRelease();
  }, [loadRelease, user]);

  async function runGateAction(action: () => Promise<ReleaseGateStatus>, done: string, failed: string) {
    setSaving(true);
    try {
      setGate(await action());
      setNotice(done);
      setError("");
      return true;
    } catch (err) {
      setError(formatErrorMessage(err, failed));
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdateStatus(status: ReleaseStatus) {
    if (releaseId === null) return;
    const ok = await runGateAction(
      () => api.updateReleaseStatus(releaseId, status),
      `Sürüm durumu "${status}" olarak güncellendi.`,
      "Sürüm durumu güncellenemedi.",
    );
    if (ok) {
      setReleases((rs) => rs.map((r) => (r.id === releaseId ? { ...r, status } : r)));
    }
  }

  async function handleUpdateCriteria(criteria: ExitCriteriaConfig) {
    if (releaseId === null) return false;
    return runGateAction(
      () => api.updateExitCriteria(releaseId, criteria),
      "Sürüm çıkış kriterleri güncellendi.",
      "Çıkış kriterleri güncellenemedi.",
    );
  }

  async function handleCreateWaiver(reason: string) {
    if (releaseId === null) return;
    await runGateAction(
      () => api.createReleaseWaiver(releaseId, reason),
      "Test Lead muafiyeti kaydedildi.",
      "Muafiyet kaydedilemedi.",
    );
  }

  async function handleDeleteWaiver() {
    if (releaseId === null) return;
    await runGateAction(
      () => api.deleteReleaseWaiver(releaseId),
      "Test Lead muafiyeti kaldırıldı.",
      "Muafiyet kaldırılamadı.",
    );
  }

  async function handleCreateSnapshot() {
    if (releaseId === null) return;
    setSaving(true);
    try {
      const snap = await api.createSummaryReportSnapshot(releaseId);
      setSnapshots((s) => [...s, snap]);
      setNotice(`Test Summary Report anlık görüntüsü #${snap.id} oluşturuldu.`);
      setError("");
    } catch (err) {
      setError(formatErrorMessage(err, "Test Summary Report anlık görüntüsü oluşturulamadı."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDownload(format: "html" | "pdf", snapshotId?: number) {
    if (releaseId === null) return;
    try {
      await api.downloadSummaryReport(releaseId, format, snapshotId);
    } catch (err) {
      setError(formatErrorMessage(err, "Test Summary Report indirilemedi."));
    }
  }

  const projectName = (id: number) => projects.find((p) => p.id === id)?.name ?? `Proje #${id}`;
  const activeSprint = sprints.find((s) => s.id === sprintId) ?? null;

  const snapshotColumns: DataTableColumn<TestSummaryReportSnapshotSummary>[] = [
    { key: "id", header: "#", render: (s) => `#${s.id}` },
    {
      key: "generated_at",
      header: "Üretim Zamanı",
      render: (s) => new Date(s.generated_at).toLocaleString("tr-TR"),
    },
    { key: "generated_by", header: "Üreten", render: (s) => s.generated_by },
    {
      key: "release_status",
      header: "Sürüm Durumu",
      render: (s) => <StatusBadge text={s.release_status} />,
    },
    {
      key: "gate_passed",
      header: "Çıkış Kapısı",
      render: (s) => (
        <span className={`badge ${s.gate_passed ? "passed" : "failed"}`}>
          {s.gate_passed ? "Geçti" : "Engelli"}
        </span>
      ),
    },
    {
      key: "download",
      header: "İndir",
      render: (s) => (
        <div className="row-actions">
          <button type="button" className="secondary-btn" onClick={() => void handleDownload("html", s.id)}>
            HTML
          </button>
          <button type="button" className="secondary-btn" onClick={() => void handleDownload("pdf", s.id)}>
            PDF
          </button>
        </div>
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

      <section>
        <div className="section-header">
          <div>
            <h2>Sürüm Yönetimi</h2>
            <p className="section-desc">
              Test Tamamlama · Sürüm durumu, çıkış kriterleri, muafiyet ve
              IEEE 829 Test Summary Report
            </p>
          </div>
          <div className="filter-group">
            <label htmlFor="release-select">Sürüm:</label>
            <select
              id="release-select"
              value={releaseId ? String(releaseId) : ""}
              onChange={(e) => setSearchParams(e.target.value ? { release: e.target.value } : {})}
            >
              {releases.map((r) => (
                <option key={r.id} value={String(r.id)}>
                  {projectName(r.project_id)} · {r.version} ({r.status})
                </option>
              ))}
            </select>
            <label htmlFor="sprint-select">Sprint:</label>
            <select
              id="sprint-select"
              value={sprintId ? String(sprintId) : ""}
              onChange={(e) =>
                setSprintChoice(
                  e.target.value && releaseId !== null
                    ? { releaseId, sprintId: Number(e.target.value) }
                    : null,
                )
              }
              disabled={sprints.length === 0}
            >
              <option value="">Tüm sprintler</option>
              {sprints.map((s) => (
                <option key={s.id} value={String(s.id)}>
                  {s.name} ({s.status})
                </option>
              ))}
            </select>
          </div>
        </div>
        {releases.length === 0 && (
          <p className="table-empty">
            Henüz sürüm yok. <Link to="/projects">Projeler &amp; Gereksinimler</Link> ekranından
            bir sürüm tanımlayın.
          </p>
        )}
      </section>

      {metrics && (
        <section>
          <div className="section-header">
            <div>
              <h2>Metrik Paneli{activeSprint ? ` · ${activeSprint.name}` : ""}</h2>
              <p className="section-desc">
                Test İzleme ve Kontrol · Seçili sürüm
                {activeSprint ? " ve sprint" : ""} kapsamında
              </p>
            </div>
          </div>
          <div className="sub-metrics">
            <div className="sub-metric-item">
              <span>Başarı Oranı</span>
              <strong>{metrics.pass_rate}%</strong>
            </div>
            <div className="sub-metric-item">
              <span>Gereksinim Kapsamı</span>
              <strong>{metrics.requirement_coverage}%</strong>
            </div>
            <div className="sub-metric-item">
              <span>Açık Defect</span>
              <strong>{metrics.open_defects}</strong>
            </div>
            <div className="sub-metric-item">
              <span>Yeniden Açılma Oranı</span>
              <strong>{metrics.reopen_rate}%</strong>
            </div>
          </div>
          <MetricsCharts metrics={metrics} />
        </section>
      )}

      <ReleaseGateCard
        gate={gate}
        user={user}
        saving={saving}
        onUpdateStatus={handleUpdateStatus}
        onUpdateCriteria={handleUpdateCriteria}
        onCreateWaiver={handleCreateWaiver}
        onDeleteWaiver={handleDeleteWaiver}
      />

      {releaseId !== null && (
        <section>
          <div className="section-header">
            <div>
              <h2>IEEE 829 Test Summary Report</h2>
              <p className="section-desc">
                Canlı rapor veya saklanmış anlık
                görüntü (snapshot)
              </p>
            </div>
            <div className="row-actions">
              <button type="button" className="secondary-btn" onClick={() => void handleDownload("html")}>
                Canlı Rapor (HTML)
              </button>
              <button type="button" className="secondary-btn" onClick={() => void handleDownload("pdf")}>
                Canlı Rapor (PDF)
              </button>
              {canCreateSnapshot && (
                <button type="button" disabled={saving} onClick={() => void handleCreateSnapshot()}>
                  Anlık Görüntü Oluştur
                </button>
              )}
            </div>
          </div>
          <DataTable
            columns={snapshotColumns}
            rows={snapshots}
            getRowKey={(s) => s.id}
            emptyMessage="Bu sürüm için henüz Test Summary Report anlık görüntüsü yok."
            ariaLabel="Test Summary Report anlık görüntüleri"
          />
        </section>
      )}
    </>
  );
}
