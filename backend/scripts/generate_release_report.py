"""PLN-36: generate v1.0 IEEE 829 Test Summary Report artifacts (HTML, PDF, JSON) for GitHub Release.

Uses an isolated temporary SQLite database migrated to head, evaluates the v1.0 release exit gate
against the repository's verification evidence, and exports standalone HTML and PDF (WeasyPrint or
RSK-07 PDF-1.4 fallback) reports plus release notes.
"""

import argparse
import importlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _render_summary_html(payload: dict[str, Any]) -> str:
    project = payload["project"]
    release = payload["release"]
    totals = payload["totals"]
    gate = payload["gate"]
    defect_summary = payload["defect_summary"]

    req_rows = "\n".join(
        f"<tr><td><strong>{r['id']}</strong></td><td>{r['title']}</td>"
        f"<td>{', '.join(r['test_cases']) if r['test_cases'] else '-'}</td>"
        f"<td>{r['passed']}</td><td>{r['failed']}</td><td>{r['not_run']}</td>"
        f"<td>{r['assessment']}</td></tr>"
        for r in payload["feature_results"]
    )
    def_rows = "\n".join(
        f"<tr><td>#{d['id']}</td><td>{d['title']}</td><td>{d['severity']}</td>"
        f"<td>{d['status']}</td><td>{d['test_case'] or '-'}</td></tr>"
        for d in payload["defects"]
    )
    gate_badge = "GEÇTİ (PASSED)" if gate["gate_passed"] else "ENGELLİ (BLOCKED)"
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <title>{payload["identifier"]} - {project["name"]} {release["version"]}</title>
  <style>
    @page {{ size: A4; margin: 20mm; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; color: #1f2937; line-height: 1.5; font-size: 13px; margin: 0; padding: 24px; }}
    header {{ border-bottom: 2px solid #1d4ed8; padding-bottom: 12px; margin-bottom: 20px; }}
    h1 {{ margin: 0 0 6px 0; font-size: 22px; color: #111827; }}
    h2 {{ margin-top: 22px; margin-bottom: 8px; font-size: 16px; color: #1e40af; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; color: #4b5563; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; margin-bottom: 16px; font-size: 12px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 6px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; font-weight: 600; }}
    footer {{ margin-top: 28px; padding-top: 10px; border-top: 1px solid #e5e7eb; font-size: 11px; color: #6b7280; }}
  </style>
</head>
<body>
  <header>
    <h1>IEEE 829 Test Summary Report · {payload["identifier"]}</h1>
    <div class="meta">
      <span><strong>Proje:</strong> {project["name"]}</span>
      <span><strong>Sürüm:</strong> {release["version"]} ({release["status"]})</span>
      <span><strong>Commit:</strong> {payload["commit"]}</span>
      <span><strong>Çıkış Kapısı:</strong> {gate_badge}</span>
      <span><strong>Üretim Zamanı:</strong> {payload["generated_at"]}</span>
    </div>
  </header>

  <section>
    <h2>1. Sürüm Test Toplamları (Overall Totals — IEEE 829 / ISO/IEC/IEEE 29119-3)</h2>
    <table>
      <thead>
        <tr><th>Toplam Vaka</th><th>Koşulan</th><th>Passed</th><th>Failed</th><th>Not Run</th><th>Koşum Oranı</th><th>Başarı Oranı</th><th>Gereksinim Kapsamı</th></tr>
      </thead>
      <tbody>
        <tr>
          <td>{totals["total_cases"]}</td><td>{totals["executed_cases"]}</td>
          <td>{totals["passed"]}</td><td>{totals["failed"]}</td><td>{totals["not_run"]}</td>
          <td>%{totals["execution_rate"]}</td><td>%{totals["pass_rate"]}</td><td>%{totals["requirement_coverage"]}</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>2. Gereksinim / Özellik Bazında Sonuçlar (Results by Feature)</h2>
    <table>
      <thead>
        <tr><th>Gereksinim</th><th>Başlık</th><th>Test Vakaları</th><th>Passed</th><th>Failed</th><th>Not Run</th><th>Değerlendirme</th></tr>
      </thead>
      <tbody>
        {req_rows}
      </tbody>
    </table>
  </section>

  <section>
    <h2>3. Defect Özeti (Defect Summary)</h2>
    <p>Toplam: <strong>{defect_summary["total"]}</strong> · Açık: <strong>{defect_summary["open_total"]}</strong> · Kapatılan: <strong>{defect_summary["closed_total"]}</strong> · Açık Critical: <strong>{defect_summary["open_critical"]}</strong></p>
    <table>
      <thead>
        <tr><th>ID</th><th>Başlık</th><th>Önem</th><th>Durum</th><th>Test Vakası</th></tr>
      </thead>
      <tbody>
        {def_rows}
      </tbody>
    </table>
  </section>

  <section>
    <h2>4. Sürüm Çıkış Kriteri Değerlendirmesi (Exit Criteria &amp; Release Gate)</h2>
    <table>
      <thead>
        <tr><th>Kriter</th><th>Hedef Eşik</th><th>Ölçülen Değer</th><th>Durum</th></tr>
      </thead>
      <tbody>
        <tr><td>Başarı Oranı (Pass Rate)</td><td>≥ %{gate["criteria"]["min_pass_rate"]}</td><td>%{gate["actual_pass_rate"]}</td><td>{"KARŞILANDI" if gate["passed_criteria"]["pass_rate"] else "EŞİK ALTINDA"}</td></tr>
        <tr><td>Açık Critical Defect</td><td>≤ {gate["criteria"]["max_open_critical"]}</td><td>{gate["actual_open_critical"]}</td><td>{"KARŞILANDI" if gate["passed_criteria"]["open_critical"] else "LİMİT AŞILDI"}</td></tr>
        <tr><td>Gereksinim Kapsamı</td><td>≥ %{gate["criteria"]["min_req_coverage"]}</td><td>%{gate["actual_req_coverage"]}</td><td>{"KARŞILANDI" if gate["passed_criteria"]["req_coverage"] else "EŞİK ALTINDA"}</td></tr>
      </tbody>
    </table>
  </section>

  <footer>
    SDS-06 Agile Test and Defect Tracking System · IEEE 829 Test Summary Report · {release["version"]} ({payload["commit"]})
  </footer>
</body>
</html>
"""


def build_release_bundle(output_dir: Path, version: str, commit: str) -> dict[str, Any]:
    backend = Path(__file__).resolve().parents[1]
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

    output_dir.mkdir(parents=True, exist_ok=True)
    from fastapi.testclient import TestClient

    from app.main import app
    from app.test_plans import _pdf_escape

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login", json={"username": "testlead", "password": "demo1234"}
        )
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        project = client.get("/api/projects", headers=headers).json()[0]
        existing_releases = client.get("/api/releases", headers=headers).json()
        rel = next(
            (
                r
                for r in existing_releases
                if r["project_id"] == project["id"] and r["version"] == version
            ),
            None,
        )
        if rel is None:
            rel_res = client.post(
                "/api/releases",
                json={"project_id": project["id"], "version": version},
                headers=headers,
            )
            rel_res.raise_for_status()
            rel = rel_res.json()

        gate = client.get(f"/api/releases/{rel['id']}/gate", headers=headers).json()
        reqs = client.get("/api/requirements", headers=headers).json()
        tcs = client.get("/api/test-cases", headers=headers).json()
        defects = client.get("/api/defects", headers=headers).json()

        tc_by_id = {tc["id"]: tc for tc in tcs}
        feature_results = []
        for r in reqs:
            linked = [tc_by_id[cid] for cid in r["test_cases"] if cid in tc_by_id]
            p_cnt = sum(1 for c in linked if c["status"] == "Passed")
            f_cnt = sum(1 for c in linked if c["status"] == "Failed")
            nr_cnt = sum(1 for c in linked if c["status"] == "Not Run")
            assessment = (
                "Doğrulandı (Passed)"
                if linked and p_cnt == len(linked)
                else "Başarısız (Failed)"
                if f_cnt > 0
                else "Kısmi / Beklemede"
                if linked
                else "Kapsam Eksik"
            )
            feature_results.append(
                {
                    "id": r["id"],
                    "title": r["title"],
                    "test_cases": r["test_cases"],
                    "passed": p_cnt,
                    "failed": f_cnt,
                    "not_run": nr_cnt,
                    "assessment": assessment,
                }
            )

        passed = sum(1 for c in tcs if c["status"] == "Passed")
        failed = sum(1 for c in tcs if c["status"] == "Failed")
        not_run = sum(1 for c in tcs if c["status"] == "Not Run")
        executed = passed + failed
        total = len(tcs)

        payload: dict[str, Any] = {
            "identifier": f"TSR-{project['name']}-{version}",
            "version": version,
            "commit": commit,
            "generated_by": "github-actions-release",
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "project": project,
            "release": rel,
            "totals": {
                "total_cases": total,
                "executed_cases": executed,
                "passed": passed,
                "failed": failed,
                "not_run": not_run,
                "execution_rate": round(executed / total * 100, 1) if total else 0.0,
                "pass_rate": gate["actual_pass_rate"],
                "requirement_coverage": gate["actual_req_coverage"],
            },
            "feature_results": feature_results,
            "defect_summary": {
                "total": len(defects),
                "open_total": sum(1 for d in defects if d["status"] != "Closed"),
                "closed_total": sum(1 for d in defects if d["status"] == "Closed"),
                "open_critical": gate["actual_open_critical"],
            },
            "defects": defects,
            "gate": gate,
        }

        html_content = _render_summary_html(payload)
        pdf_bytes: bytes | None = None
        try:
            weasyprint = importlib.import_module("weasyprint")
            candidate = weasyprint.HTML(string=html_content).write_pdf()
            if isinstance(candidate, bytes) and candidate.startswith(b"%PDF-"):
                pdf_bytes = candidate
        except Exception:
            pdf_bytes = None

        if pdf_bytes is None:
            lines = [
                f"IEEE 829 / ISO/IEC/IEEE 29119-3 TEST SUMMARY REPORT: {payload['identifier']}",
                f"Project: {project['name']} | Release: {version} | Commit: {commit}",
                f"Generated at: {payload['generated_at']}",
                "-" * 72,
                f"Totals: Cases={total}, Executed={executed}, Passed={passed}, Failed={failed}, NotRun={not_run}",
                f"Pass Rate={gate['actual_pass_rate']}% | Requirement Coverage={gate['actual_req_coverage']}% | Open Critical={gate['actual_open_critical']}",
                "Feature Results:",
                *(
                    f"  - {r['id']}: P={r['passed']} F={r['failed']} NR={r['not_run']} ({r['assessment']})"
                    for r in feature_results
                ),
                "Defects:",
                *(
                    f"  - #{d['id']} {d['title']} [{d['severity']} / {d['status']}]"
                    for d in defects
                ),
            ]
            stream_cmds = ["BT", "/F1 10 Tf", "50 790 Td", "13 TL"]
            for idx, line in enumerate(lines):
                esc = _pdf_escape(line)
                stream_cmds.append(f"({esc}) Tj" if idx == 0 else f"T* ({esc}) Tj")
            stream_cmds.append("ET")
            stream_data = "\n".join(stream_cmds).encode("latin-1")
            objects = [
                b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
                b"2 0 obj\n<< /Type /Pages /Kids [4 0 R] /Count 1 >>\nendobj\n",
                b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
                b"4 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>\nendobj\n",
                f"5 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode("latin-1")
                + stream_data
                + b"\nendstream\nendobj\n",
            ]
            out = bytearray(b"%PDF-1.4\n")
            offsets = []
            for obj in objects:
                offsets.append(len(out))
                out.extend(obj)
            xref_pos = len(out)
            out.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1"))
            for off in offsets:
                out.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
            out.extend(
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
                    "latin-1"
                )
            )
            pdf_bytes = bytes(out)

        safe_ver = "".join(ch if (ch.isalnum() or ch in ("-", "_", ".")) else "_" for ch in version)
        html_path = output_dir / f"test-summary-report-{safe_ver}.html"
        pdf_path = output_dir / f"test-summary-report-{safe_ver}.pdf"
        json_path = output_dir / f"test-summary-report-{safe_ver}.json"
        notes_path = output_dir / f"release-notes-{safe_ver}.md"

        html_path.write_text(html_content, encoding="utf-8")
        pdf_path.write_bytes(pdf_bytes)
        json_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        notes_path.write_text(
            f"# SDS-06 {version} — Release Notes\n\n"
            f"- **Standart Çerçevesi:** ISO/IEC/IEEE 12207 · IEEE 829 · ISO/IEC/IEEE 29119-2 / 29119-3\n"
            f"- **Commit:** `{commit}`\n"
            f"- **Test Summary Report ID:** `{payload['identifier']}`\n"
            f"- **Başarı Oranı (Pass Rate):** `%{gate['actual_pass_rate']}`\n"
            f"- **Gereksinim Kapsamı (Requirement Coverage):** `%{gate['actual_req_coverage']}`\n"
            f"- **Açık Critical Defect:** `{gate['actual_open_critical']}`\n\n"
            f"## Ekler (Release Assets)\n\n"
            f"- `{pdf_path.name}` — IEEE 829 Test Summary Report (PDF)\n"
            f"- `{html_path.name}` — IEEE 829 Test Summary Report (HTML)\n"
            f"- `{json_path.name}` — Makinece okunabilir özet rapor kanıtı (JSON)\n",
            encoding="utf-8",
        )
        return {
            "html_path": str(html_path),
            "pdf_path": str(pdf_path),
            "json_path": str(json_path),
            "notes_path": str(notes_path),
            "payload": payload,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="v1.0.0")
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--output-dir", type=Path, default=Path("release-artifacts"))
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--coverage", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    if any((args.junit, args.coverage, args.evidence)):
        if not all((args.junit, args.coverage, args.evidence)):
            parser.error("--junit, --coverage and --evidence are required together")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from scripts.release_evidence import build_bundle

        payload = build_bundle(
            args.output_dir, args.version, args.commit, args.junit, args.coverage, args.evidence
        )
        if not payload["gate"]["gate_passed"]:
            raise SystemExit(
                "Actual test-evidence release gate failed; report retained for diagnosis"
            )
        print("Generated Test Summary Report from actual test evidence")
        return
    backend = Path(__file__).resolve().parents[1]
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    with tempfile.TemporaryDirectory(prefix="sds06-release-v1-") as directory:
        os.environ["DATABASE_URL"] = f"sqlite:///{directory}/release.db"
        from alembic import command
        from alembic.config import Config
        from app.db import engine

        config = Config(str(backend / "alembic.ini"))
        config.set_main_option("script_location", str(backend / "alembic"))
        try:
            command.upgrade(config, "head")
            bundle = build_release_bundle(args.output_dir, args.version, args.commit)
            print(f"Generated release bundle in {args.output_dir}: {bundle['pdf_path']}")
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
