// PLN-35: real HTTP + Chromium measurements, no mocked APIs or fabricated timings.
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import os from "node:os";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { stripVTControlCharacters } from "node:util";
import { chromium } from "playwright";

assert.equal(process.env.PLN35_DISPOSABLE, "1", "Only run against a disposable database");
const root = fileURLToPath(new URL("../", import.meta.url));
const python = process.env.PYTHON ?? "python";
const seeded = spawnSync(python, ["scripts/seed_quality.py"], { cwd: `${root}backend`, encoding: "utf8", env: process.env });
if (seeded.status !== 0) throw new Error(`Fixture creation failed: ${seeded.stderr}\n${seeded.stdout}`);
const fixture = JSON.parse(seeded.stdout.trim().split("\n").at(-1));
const children = [];
async function start(command, args, cwd, marker) {
  const child = spawn(command, args, { cwd, env: process.env, stdio: ["ignore", "pipe", "pipe"] });
  children.push(child);
  await new Promise((resolve, reject) => {
    let logs = "";
    const timeout = setTimeout(() => reject(new Error(`${command} startup timed out: ${stripVTControlCharacters(logs)}`)), 30_000);
    const chunk = data => {
      logs = (logs + data.toString()).slice(-4000);
      if (stripVTControlCharacters(logs).includes(marker)) { clearTimeout(timeout); resolve(); }
    };
    child.stdout.on("data", chunk);
    child.stderr.on("data", chunk);
    child.once("error", error => { clearTimeout(timeout); reject(error); });
    child.once("exit", code => { clearTimeout(timeout); reject(new Error(`${command} exited (${code}): ${logs}`)); });
  });
}
const results = {
  measured_at: new Date().toISOString(),
  commit: process.env.REPORT_COMMIT ?? spawnSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).stdout.trim(),
  environment: { os: os.release(), platform: os.platform(), cpu: os.cpus()[0].model, logical_cpus: os.cpus().length,
    memory_bytes: os.totalmem(), node: process.version, runner: process.env.GITHUB_ACTIONS ? "GitHub Actions ubuntu-latest" : "local" },
  fixture,
  measurements: {},
};
function summarize(samples, limit) {
  const sorted = [...samples].sort((a, b) => a - b);
  const max = sorted.at(-1);
  return { unit: "ms", samples, first: samples[0], min: sorted[0], median: sorted[Math.floor(sorted.length / 2)],
    p95: sorted[Math.ceil(sorted.length * 0.95) - 1], max, limit_ms: limit, passed: max < limit };
}
const apiURL = "http://127.0.0.1:8000";
let browser;
try {
  await start(python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], `${root}backend`, "Application startup complete.");
  await start(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", "5175", "--strictPort"], `${root}frontend`, "http://127.0.0.1:5175");
  const login = await fetch(`${apiURL}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: "admin", password: "demo1234" }) });
  assert.equal(login.status, 200);
  const token = (await login.json()).access_token;
  const headers = { Authorization: `Bearer ${token}` };
  browser = await chromium.launch(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } : {});
  results.environment.chromium = browser.version();
  assert.ok(fixture.executions === 10_000 && fixture.panel_executions >= fixture.executions);
  const samples = [];
  results.panel_diagnostics = [];
  const sampleCount = Number(process.env.PLN35_SAMPLES ?? 10);
  assert.ok(Number.isInteger(sampleCount) && sampleCount >= (process.env.GITHUB_ACTIONS ? 10 : 1));
  for (let i = 0; i < sampleCount; i++) {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
    try {
      await context.addInitScript(value => localStorage.setItem("token", value), token);
      const page = await context.newPage();
      const apiRequests = [];
      page.on("requestfinished", request => {
        if (new URL(request.url()).pathname.startsWith("/api/")) apiRequests.push({ path: new URL(request.url()).pathname, timing: request.timing() });
      });
      const responses = ["/api/metrics", "/api/test-cases", "/api/defects", "/api/projects", "/api/releases", "/api/requirements", `/api/metrics/expanded?release_id=${fixture.release_id}`, `/api/releases/${fixture.release_id}/gate`]
        .map(path => page.waitForResponse(r => new URL(r.url()).pathname + new URL(r.url()).search === path, { timeout: 30_000 }));
      const before = performance.now();
      await page.goto("http://127.0.0.1:5175/", { waitUntil: "load" });
      const navigationMs = performance.now() - before;
      const loaded = await Promise.all(responses);
      const apiMs = performance.now() - before;
      for (const response of loaded) assert.equal(response.status(), 200, response.url());
      const metrics = await loaded[6].json();
      assert.equal(metrics.total_tests, fixture.panel_executions);
      assert.equal(metrics.pass_rate, fixture.panel_pass_rate);
      assert.equal(metrics.denominators.planned_executions, fixture.panel_executions);
      await page.getByRole("heading", { name: "Grafikli Metrik Paneli (R5)", exact: true }).waitFor();
      await page.locator(".metrics .card").filter({ hasText: "Toplam Test" }).getByText(String(fixture.panel_executions), { exact: true }).waitFor();
      await page.getByRole("img", { name: "Koşum başına yığılmış test sonuçları ve başarı oranı trend grafiği", exact: true }).waitFor();
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      const totalMs = performance.now() - before;
      samples.push(totalMs);
      for (const path of ["/api/metrics", "/api/test-cases", "/api/defects", "/api/projects", "/api/releases", "/api/requirements", "/api/metrics/expanded", `/api/releases/${fixture.release_id}/gate`]) {
        assert.equal(apiRequests.filter(r => r.path === path).length, 1, `Duplicate or missing dashboard request: ${path}`);
      }
      results.panel_diagnostics.push({ navigation_ms: navigationMs, api_ready_ms: apiMs, paint_ms: totalMs, requests: apiRequests });
    } finally { await context.close(); }
  }
  results.measurements.panel_navigation = summarize(samples, 2000);
  // A faster initial load must preserve the release selector's observable behavior.
  const control = await browser.newContext();
  try {
    await control.addInitScript(value => localStorage.setItem("token", value), token);
    const page = await control.newPage();
    await page.goto("http://127.0.0.1:5175/");
    const selector = page.getByLabel("Sürüm:", { exact: true });
    const card = page.locator(".metrics .card").filter({ hasText: "Toplam Test" });
    await card.getByText(String(fixture.panel_executions), { exact: true }).waitFor();
    let changed = page.waitForResponse(r => r.url().endsWith(`/api/metrics/expanded?release_id=${fixture.empty_release_id}`));
    await selector.selectOption(String(fixture.empty_release_id));
    assert.equal((await (await changed).json()).total_tests, 0);
    await card.getByText("0", { exact: true }).waitFor();
    changed = page.waitForResponse(r => r.url().endsWith(`/api/metrics/expanded?release_id=${fixture.release_id}`));
    await selector.selectOption(String(fixture.release_id));
    assert.equal((await (await changed).json()).total_tests, fixture.panel_executions);
    await card.getByText(String(fixture.panel_executions), { exact: true }).waitFor();
    results.release_selector_verified = true;
    const anonymousRequests = [];
    page.on("request", r => { if (new URL(r.url()).pathname.startsWith("/api/")) anonymousRequests.push(r.url()); });
    await page.getByRole("button", { name: "Çıkış Yap", exact: true }).click();
    await page.getByRole("link", { name: "Giriş Yap", exact: true }).waitFor();
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert.equal(await page.locator(".metrics .card").count(), 0);
    assert.deepEqual(anonymousRequests, [], "Anonymous dashboard must not request protected data");
    results.anonymous_dashboard_verified = true;
  } finally { await control.close(); }
  const operations = {
    test_plan_html: [`/api/test-plans/${fixture.plan_id}/export?format=html`, "GET", "text/html"],
    test_plan_pdf: [`/api/test-plans/${fixture.plan_id}/export?format=pdf`, "GET", "application/pdf"],
    test_plan_snapshot: [`/api/test-plans/${fixture.plan_id}/snapshots`, "POST", "application/json"],
  };
  for (const [name, [path, method, type]] of Object.entries(operations)) {
    const durations = [];
    for (let i = 0; i < 5; i++) {
      const before = performance.now();
      const response = await fetch(apiURL + path, { headers, method });
      const bytes = Buffer.from(await response.arrayBuffer());
      durations.push(performance.now() - before);
      assert.equal(response.status, method === "POST" ? 201 : 200);
      assert.ok(response.headers.get("content-type").includes(type));
      if (type === "application/pdf") { assert.equal(bytes.subarray(0, 5).toString(), "%PDF-"); assert.ok(bytes.includes(Buffer.from("%%EOF"))); }
      else if (type === "text/html") assert.ok(bytes.toString().includes("PLN-35 measured Test Plan"));
      else assert.equal(JSON.parse(bytes).test_plan_id, fixture.plan_id);
    }
    results.measurements[name] = summarize(durations, 10_000);
  }
  results.passed = Object.values(results.measurements).every(m => m.passed);
} finally {
  if (browser) await browser.close();
  for (const child of children.reverse()) {
    if (child.exitCode === null && child.signalCode === null) {
      const stopped = new Promise(resolve => child.once("exit", resolve));
      child.kill("SIGTERM");
      await stopped;
    }
  }
  await mkdir(new URL("results/", import.meta.url), { recursive: true });
  await writeFile(new URL("results/performance.json", import.meta.url), JSON.stringify(results, null, 2) + "\n");
}
console.log("PLN35_MEASUREMENTS=" + JSON.stringify(results));
assert.equal(results.passed, true, "A measured maximum exceeded its acceptance threshold");
