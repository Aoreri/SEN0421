import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ExitCriteriaConfig,
  RELEASE_STATUSES,
  ReleaseGateStatus,
  ReleaseStatus,
  User,
} from "../api";
import {
  ExitCriteriaFormErrors,
  hasFormErrors,
  validateExitCriteriaForm,
  validateWaiverReason,
} from "../validation";
import { StatusBadge } from "./StatusBadge";
import { useLang, useT } from "../i18n";

export type ReleaseGateCardProps = {
  gate: ReleaseGateStatus | null;
  user: User | null;
  saving: boolean;
  onUpdateStatus: (status: ReleaseStatus) => Promise<void>;
  onUpdateCriteria: (criteria: ExitCriteriaConfig) => Promise<boolean>;
  onCreateWaiver: (reason: string) => Promise<void>;
  onDeleteWaiver: () => Promise<void>;
  /** Paneldeki kartta sürüm yönetimi ekranına bağlantı gösterir. */
  showManageLink?: boolean;
};

export function ReleaseGateCard({
  gate,
  user,
  saving,
  onUpdateStatus,
  onUpdateCriteria,
  onCreateWaiver,
  onDeleteWaiver,
  showManageLink = false,
}: ReleaseGateCardProps) {
  const t = useT();
  const lang = useLang();
  const [editingCriteria, setEditingCriteria] = useState(false);
  const [minPassRate, setMinPassRate] = useState("80");
  const [maxOpenCritical, setMaxOpenCritical] = useState("0");
  const [minReqCoverage, setMinReqCoverage] = useState("80");
  const [criteriaErrors, setCriteriaErrors] = useState<ExitCriteriaFormErrors>({});

  const [waiverReason, setWaiverReason] = useState("");
  const [waiverError, setWaiverError] = useState("");

  useEffect(() => {
    if (!gate) return;
    setMinPassRate(String(gate.criteria.min_pass_rate));
    setMaxOpenCritical(String(gate.criteria.max_open_critical));
    setMinReqCoverage(String(gate.criteria.min_req_coverage));
  }, [gate]);

  if (!gate) {
    return (
      <section>
        <h2>{t("Sürüm Çıkış Kapısı")}</h2>
        <p className="table-empty">
          {t("Çıkış kapısı değerlendirmesi için önce bir sürüm tanımlayın.")}
        </p>
      </section>
    );
  }

  const canManageGate =
    user !== null && (user.role === "Admin" || user.role === "Test Lead");
  // FR-REL-03: the API lets Admin and Test Lead record or remove a waiver.
  const canWaive = canManageGate;

  async function handleSaveCriteria(e: FormEvent) {
    e.preventDefault();
    const errs = validateExitCriteriaForm({
      minPassRate,
      maxOpenCritical,
      minReqCoverage,
    });
    setCriteriaErrors(errs);
    if (hasFormErrors(errs)) return;

    const ok = await onUpdateCriteria({
      min_pass_rate: Number(minPassRate),
      max_open_critical: Number(maxOpenCritical),
      min_req_coverage: Number(minReqCoverage),
    });
    if (ok) {
      setEditingCriteria(false);
    }
  }

  async function handleWaiverSubmit(e: FormEvent) {
    e.preventDefault();
    const err = validateWaiverReason(waiverReason);
    if (err) {
      setWaiverError(err);
      return;
    }
    setWaiverError("");
    await onCreateWaiver(waiverReason.trim());
    setWaiverReason("");
  }

  return (
    <section className="release-gate-section">
      <div className="section-header">
        <div>
          <h2>
            {t("Sürüm Çıkış Kapısı:")} {gate.release_version}
          </h2>
          <p className="section-desc">
            {t("Test İzleme ve Kontrol · Sürüm Yayınlama Kriterleri")}
          </p>
        </div>
        <div className="badge-list">
          <StatusBadge text={gate.status} />
          <span className={`badge ${gate.gate_passed ? "passed" : "failed"}`}>
            {gate.gate_passed ? t("Çıkış Kapısı Geçti") : t("Çıkış Kapısı Engelli")}
          </span>
        </div>
      </div>

      <div className="gate-criteria-grid">
        <div
          className={`gate-criterion ${gate.passed_criteria.pass_rate ? "ok" : "fail"}`}
        >
          <span className="detail-label">{t("Test Başarı Oranı")}</span>
          <strong>
            {gate.actual_pass_rate}%{" "}
            <span className="hint">
              {t("/ hedef ≥ {target}%", { target: gate.criteria.min_pass_rate })}
            </span>
          </strong>
          <span className={`badge ${gate.passed_criteria.pass_rate ? "passed" : "failed"}`}>
            {gate.passed_criteria.pass_rate ? t("Karşılandı") : t("Eşik Altında")}
          </span>
        </div>

        <div
          className={`gate-criterion ${gate.passed_criteria.open_critical ? "ok" : "fail"}`}
        >
          <span className="detail-label">{t("Açık Critical Defect")}</span>
          <strong>
            {gate.actual_open_critical}{" "}
            <span className="hint">
              {t("/ limit ≤ {limit}", { limit: gate.criteria.max_open_critical })}
            </span>
          </strong>
          <span className={`badge ${gate.passed_criteria.open_critical ? "passed" : "failed"}`}>
            {gate.passed_criteria.open_critical ? t("Karşılandı") : t("Limit Aşıldı")}
          </span>
        </div>

        <div
          className={`gate-criterion ${gate.passed_criteria.req_coverage ? "ok" : "fail"}`}
        >
          <span className="detail-label">{t("Gereksinim Kapsamı")}</span>
          <strong>
            {gate.actual_req_coverage}%{" "}
            <span className="hint">
              {t("/ hedef ≥ {target}%", { target: gate.criteria.min_req_coverage })}
            </span>
          </strong>
          <span className={`badge ${gate.passed_criteria.req_coverage ? "passed" : "failed"}`}>
            {gate.passed_criteria.req_coverage ? t("Karşılandı") : t("Eşik Altında")}
          </span>
        </div>
      </div>

      {gate.waiver && (
        <div className="waiver-banner" role="note">
          <div style={{ flex: 1 }}>
            <strong>
              {gate.passed_criteria.pass_rate &&
              gate.passed_criteria.open_critical &&
              gate.passed_criteria.req_coverage
                ? t("Kayıtlı Test Lead Muafiyeti (Kriterler sağlandığı için pasif):")
                : t("Aktif Test Lead Muafiyeti:")}
            </strong>{" "}
            {gate.waiver.reason}{" "}
            <span className="hint">
              ({t("Onaylayan:")} <strong>{gate.waiver.waived_by}</strong> ·{" "}
              {new Date(gate.waiver.waived_at).toLocaleString(
                lang === "tr" ? "tr-TR" : "en-GB",
              )})
            </span>
          </div>
          {canWaive && (
            <button
              type="button"
              className="secondary-btn"
              disabled={saving}
              onClick={() => void onDeleteWaiver()}
            >
              {t("Muafiyeti Kaldır")}
            </button>
          )}
        </div>
      )}

      <div className="gate-actions-bar">
        <div className="row-actions">
          <span className="detail-label">{t("Sürüm Durumu:")}</span>
          {RELEASE_STATUSES.map((status) => {
            const requiresGate = status === "Ready" || status === "Released";
            const blockedByGate = requiresGate && !gate.gate_passed;
            return (
              <button
                key={status}
                type="button"
                className={gate.status === status ? "" : "secondary-btn"}
                disabled={!canManageGate || saving || blockedByGate || gate.status === status}
                title={
                  blockedByGate
                    ? t(
                        "Çıkış kriterleri karşılanmadan veya muafiyet girilmeden Ready/Released yapılamaz",
                      )
                    : undefined
                }
                onClick={() => void onUpdateStatus(status)}
              >
                {status}
              </button>
            );
          })}
        </div>

        {canManageGate && (
          <button
            type="button"
            className="secondary-btn"
            onClick={() => setEditingCriteria((v) => !v)}
          >
            {editingCriteria ? t("Eşikleri Gizle") : t("Çıkış Eşikleri Düzenle")}
          </button>
        )}

        {showManageLink && (
          <Link to={`/releases?release=${gate.release_id}`} className="detail-link">
            {t("Sürüm Yönetimi & Test Summary Report →")}
          </Link>
        )}
      </div>

      {!canManageGate && (
        <p className="hint" style={{ marginTop: 8 }}>
          {t("Sürüm durumu güncelleme ve eşik yapılandırma yalnızca")}{" "}
          <strong>Test Lead</strong> {t("ve")} <strong>Admin</strong>{" "}
          {t("rolleri içindir.")}
        </p>
      )}

      {editingCriteria && canManageGate && (
        <form onSubmit={(e) => void handleSaveCriteria(e)} className="gate-subform" noValidate>
          <div className="form-grid">
            <div className="form-field">
              <label htmlFor="crit-pass">{t("Min. Başarı Oranı (%)")}</label>
              <input
                id="crit-pass"
                type="number"
                min={0}
                max={100}
                value={minPassRate}
                onChange={(e) => setMinPassRate(e.target.value)}
              />
              {criteriaErrors.minPassRate && (
                <span className="field-error">{criteriaErrors.minPassRate}</span>
              )}
            </div>
            <div className="form-field">
              <label htmlFor="crit-crit">{t("Maks. Açık Critical Defect")}</label>
              <input
                id="crit-crit"
                type="number"
                min={0}
                value={maxOpenCritical}
                onChange={(e) => setMaxOpenCritical(e.target.value)}
              />
              {criteriaErrors.maxOpenCritical && (
                <span className="field-error">{criteriaErrors.maxOpenCritical}</span>
              )}
            </div>
            <div className="form-field">
              <label htmlFor="crit-cov">{t("Min. Gereksinim Kapsamı (%)")}</label>
              <input
                id="crit-cov"
                type="number"
                min={0}
                max={100}
                value={minReqCoverage}
                onChange={(e) => setMinReqCoverage(e.target.value)}
              />
              {criteriaErrors.minReqCoverage && (
                <span className="field-error">{criteriaErrors.minReqCoverage}</span>
              )}
            </div>
          </div>
          <div className="row-actions">
            <button type="submit" disabled={saving}>
              {t("Eşikleri Kaydet")}
            </button>
          </div>
        </form>
      )}

      {canWaive && !gate.gate_passed && (
        <form onSubmit={(e) => void handleWaiverSubmit(e)} className="gate-subform" noValidate>
          <div className="form-field" style={{ flex: 1, width: "100%" }}>
            <label htmlFor="waiver-reason">
              {t(
                "Test Lead Muafiyeti Gerekçesi (Kriterler karşılanmasa da sürüm çıkışını onaylamak için)",
              )}
            </label>
            <input
              id="waiver-reason"
              value={waiverReason}
              onChange={(e) => {
                setWaiverReason(e.target.value);
                if (waiverError) setWaiverError("");
              }}
              placeholder={t(
                "Örn: Bilinen düşük etkili sorun sonraki yamaya ertelendi.",
              )}
            />
            {waiverError && (
              <span className="field-error" role="alert">
                {waiverError}
              </span>
            )}
          </div>
          <div className="row-actions">
            <button type="submit" disabled={saving}>
              {t("Muafiyet Kaydet")}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
