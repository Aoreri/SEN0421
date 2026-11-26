import {
  DefectBurnupPoint,
  ExpandedMetrics,
  RunMetricPoint,
  SeverityDistributionItem,
} from "../api";
import { useT } from "../i18n";

export type MetricsChartsProps = {
  metrics: ExpandedMetrics;
};

function shortLabel(text: string, maxLen = 14): string {
  return text.length > maxLen ? `${text.slice(0, maxLen - 1)}…` : text;
}

function StackedRunTrendChart({ series }: { series: RunMetricPoint[] }) {
  const t = useT();
  if (series.length === 0) {
    return <p className="table-empty">{t("Grafik için henüz test koşumu verisi yok.")}</p>;
  }

  const width = 520;
  const height = 240;
  const pad = { top: 20, right: 44, bottom: 50, left: 36 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const maxTotal = Math.max(
    1,
    ...series.map((p) => p.passed + p.failed + p.blocked + p.skipped + p.not_run),
  );
  const slotW = plotW / series.length;
  const barW = Math.min(44, Math.max(16, slotW * 0.56));

  const trendPoints = series.map((p, idx) => {
    const cx = pad.left + slotW * idx + slotW / 2;
    const cy = pad.top + plotH - (p.pass_rate / 100) * plotH;
    return { cx, cy, rate: p.pass_rate, name: p.run_name };
  });

  const polylinePts = trendPoints.map((pt) => `${pt.cx},${pt.cy}`).join(" ");

  return (
    <div className="chart-card">
      <div className="chart-header">
        <h3>{t("Koşum Başına Sonuç Dağılımı & Başarı Trendi")}</h3>
        <div className="chart-legend">
          <span>
            <i className="legend-dot passed" /> Passed
          </span>
          <span>
            <i className="legend-dot failed" /> Failed
          </span>
          <span>
            <i className="legend-dot blocked" /> Blocked
          </span>
          <span>
            <i className="legend-dot skipped" /> Skipped
          </span>
          <span>
            <i className="legend-line" /> {t("Başarı %")}
          </span>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="chart-svg"
        role="img"
        aria-label={t("Koşum başına yığılmış test sonuçları ve başarı oranı trend grafiği")}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = pad.top + plotH * (1 - ratio);
          return (
            <g key={ratio}>
              <line
                x1={pad.left}
                y1={y}
                x2={width - pad.right}
                y2={y}
                stroke="#e2e8f0"
                strokeDasharray="3 3"
              />
              <text
                x={pad.left - 6}
                y={y + 4}
                textAnchor="end"
                fontSize="10"
                fill="#64748b"
              >
                {Math.round(maxTotal * ratio)}
              </text>
              <text
                x={width - pad.right + 6}
                y={y + 4}
                textAnchor="start"
                fontSize="10"
                fill="#1d4ed8"
              >
                {Math.round(ratio * 100)}%
              </text>
            </g>
          );
        })}

        {series.map((point, idx) => {
          const x = pad.left + slotW * idx + (slotW - barW) / 2;
          const cx = pad.left + slotW * idx + slotW / 2;
          const segments: Array<{ key: string; count: number; color: string }> = [
            { key: "Passed", count: point.passed, color: "#10b981" },
            { key: "Failed", count: point.failed, color: "#ef4444" },
            { key: "Blocked", count: point.blocked, color: "#f59e0b" },
            { key: "Skipped", count: point.skipped, color: "#94a3b8" },
            { key: "Not Run", count: point.not_run, color: "#cbd5e1" },
          ];

          let currentY = pad.top + plotH;
          return (
            <g key={point.run_id}>
              {segments.map((seg) => {
                if (seg.count <= 0) return null;
                const segH = (seg.count / maxTotal) * plotH;
                currentY -= segH;
                return (
                  <rect
                    key={seg.key}
                    x={x}
                    y={currentY}
                    width={barW}
                    height={segH}
                    fill={seg.color}
                    rx={2}
                  >
                    <title>
                      {`${point.run_name} · ${seg.key}: ${seg.count}`}
                    </title>
                  </rect>
                );
              })}
              <text
                x={cx}
                y={height - 24}
                textAnchor="middle"
                fontSize="10"
                fill="#334155"
              >
                {`#${point.run_id}`}
              </text>
              <text
                x={cx}
                y={height - 10}
                textAnchor="middle"
                fontSize="9"
                fill="#64748b"
              >
                {shortLabel(point.run_name, 12)}
              </text>
            </g>
          );
        })}

        {trendPoints.length > 1 && (
          <polyline
            fill="none"
            stroke="#1d4ed8"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={polylinePts}
          />
        )}

        {trendPoints.map((pt, idx) => (
          <g key={idx}>
            <circle cx={pt.cx} cy={pt.cy} r={4.5} fill="#ffffff" stroke="#1d4ed8" strokeWidth="2.5">
              <title>{`${pt.name}: %${pt.rate} ${t("başarı oranı")}`}</title>
            </circle>
            <text
              x={pt.cx}
              y={Math.max(12, pt.cy - 8)}
              textAnchor="middle"
              fontSize="10"
              fontWeight="600"
              fill="#1e3a8a"
            >
              {pt.rate}%
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function DefectBurnUpChart({ points }: { points: DefectBurnupPoint[] }) {
  const t = useT();
  if (points.length === 0) {
    return <p className="table-empty">{t("Defect burn-up için henüz zaman serisi verisi yok.")}</p>;
  }

  const width = 460;
  const height = 220;
  const pad = { top: 20, right: 20, bottom: 38, left: 36 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const maxY = Math.max(1, ...points.map((p) => Math.max(p.opened, p.closed)));

  const xAt = (idx: number) =>
    points.length === 1
      ? pad.left + plotW / 2
      : pad.left + (idx / (points.length - 1)) * plotW;
  const yAt = (val: number) => pad.top + plotH - (val / maxY) * plotH;

  const openedPts = points.map((p, idx) => `${xAt(idx)},${yAt(p.opened)}`).join(" ");
  const closedPts = points.map((p, idx) => `${xAt(idx)},${yAt(p.closed)}`).join(" ");
  const latest = points[points.length - 1];

  return (
    <div className="chart-card">
      <div className="chart-header">
        <h3>{t("Defect Burn-up (Açılan vs Kapatılan)")}</h3>
        <div className="chart-legend">
          <span>
            <i className="legend-dot failed" /> {t("Açılan")} ({latest.opened})
          </span>
          <span>
            <i className="legend-dot passed" /> {t("Kapatılan")} ({latest.closed})
          </span>
          <span className="badge">
            {t("Açık Kalan: {count}", { count: latest.open_remaining })}
          </span>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="chart-svg"
        role="img"
        aria-label={t("Zaman içinde açılan ve kapatılan defect burn-up grafiği")}
      >
        {[0, 0.5, 1].map((ratio) => {
          const y = pad.top + plotH * (1 - ratio);
          return (
            <g key={ratio}>
              <line
                x1={pad.left}
                y1={y}
                x2={width - pad.right}
                y2={y}
                stroke="#e2e8f0"
                strokeDasharray="3 3"
              />
              <text x={pad.left - 6} y={y + 4} textAnchor="end" fontSize="10" fill="#64748b">
                {Math.round(maxY * ratio)}
              </text>
            </g>
          );
        })}

        {points.length > 1 && (
          <>
            <polyline
              fill="none"
              stroke="#ef4444"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={openedPts}
            />
            <polyline
              fill="none"
              stroke="#10b981"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={closedPts}
            />
          </>
        )}

        {points.map((p, idx) => {
          const cx = xAt(idx);
          return (
            <g key={p.date}>
              <circle cx={cx} cy={yAt(p.opened)} r={4} fill="#ef4444">
                <title>{`${p.date} · ${t("Toplam Açılan:")} ${p.opened}`}</title>
              </circle>
              <circle cx={cx} cy={yAt(p.closed)} r={4} fill="#10b981">
                <title>{`${p.date} · ${t("Toplam Kapatılan:")} ${p.closed}`}</title>
              </circle>
              <text
                x={cx}
                y={height - 12}
                textAnchor="middle"
                fontSize="10"
                fill="#475569"
              >
                {p.date.slice(5)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function SeverityDistributionChart({ items }: { items: SeverityDistributionItem[] }) {
  const t = useT();
  const maxTotal = Math.max(1, ...items.map((item) => item.total));
  const ordered = [...items].reverse();

  return (
    <div className="chart-card">
      <div className="chart-header">
        <h3>{t("Önem Derecesine Göre Defect Dağılımı")}</h3>
        <div className="chart-legend">
          <span>
            <i className="legend-dot failed" /> {t("Açık / İşlemde")}
          </span>
          <span>
            <i className="legend-dot passed" /> {t("Kapatılan")}
          </span>
        </div>
      </div>

      <div className="severity-bars">
        {ordered.map((item) => {
          const openPct = (item.open / maxTotal) * 100;
          const closedPct = (item.closed / maxTotal) * 100;
          return (
            <div key={item.severity} className="severity-bar-row">
              <div className="severity-label-col">
                <span className={`badge ${item.severity.toLowerCase()}`}>{item.severity}</span>
              </div>
              <div
                className="severity-track"
                role="img"
                aria-label={`${item.severity}: ${t("{count} açık, {closed} kapalı", { count: item.open, closed: item.closed })}`}
              >
                {item.open > 0 && (
                  <div
                    className="severity-seg open-seg"
                    style={{ width: `${openPct}%` }}
                    title={`${item.severity} ${t("Açık:")} ${item.open}`}
                  />
                )}
                {item.closed > 0 && (
                  <div
                    className="severity-seg closed-seg"
                    style={{ width: `${closedPct}%` }}
                    title={`${item.severity} ${t("Kapatılan:")} ${item.closed}`}
                  />
                )}
              </div>
              <div className="severity-count-col">
                <strong>{item.total}</strong>{" "}
                <span className="hint">
                  ({t("{count} açık", { count: item.open })})
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function MetricsCharts({ metrics }: MetricsChartsProps) {
  return (
    <div className="charts-grid">
      <div className="charts-grid-wide">
        <StackedRunTrendChart series={metrics.run_series} />
      </div>
      <DefectBurnUpChart points={metrics.defect_burnup} />
      <SeverityDistributionChart items={metrics.severity_distribution} />
    </div>
  );
}
