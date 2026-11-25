// Import the unmodified Playwright JUnit report into the same disposable Compose app.
import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";

assert.equal(process.env.E2E_DISPOSABLE, "1", "Only import into a disposable SDS-06 instance");
const baseURL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:5173";
const fixture = JSON.parse(await readFile("test-results/fixture.json", "utf8"));
const junit = await readFile("test-results/junit.xml");
const commit = process.env.REPORT_COMMIT;
const branch = process.env.REPORT_BRANCH;
assert.match(commit ?? "", /^[a-fA-F0-9]{7,64}$/, "REPORT_COMMIT must identify the tested commit");
assert.ok(branch?.trim(), "REPORT_BRANCH must identify the tested branch");
async function json(path, options = {}, expected = 200) {
  const response = await fetch(new URL(path, baseURL), options);
  assert.equal(response.status, expected, `${path}: HTTP ${response.status}`);
  return response.json();
}
const auth = await json("/api/auth/login", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ username: "admin", password: "demo1234" }),
});
const headers = { Authorization: `Bearer ${auth.access_token}` };
const query = new URLSearchParams({ commit, branch });
const report = await json(`/api/projects/${fixture.projectId}/runs/import?${query}`, {
  method: "POST", headers: { ...headers, "Content-Type": "application/xml" }, body: junit,
}, 201);
assert.equal(report.summary.total, 3, "All three acceptance scenarios must be reported");
assert.equal(report.summary.matched, 3);
assert.equal(report.summary.unmatched, 0);
assert.deepEqual(report.results.map(r => r.test_case_id).sort(), Object.values(fixture.cases).sort());
const saved = await json(`/api/projects/${fixture.projectId}/runs/imports/${report.id}`, { headers });
assert.deepEqual(saved, report, "Persisted import must match the POST response");
assert.equal(saved.commit, commit);
assert.equal(saved.branch, branch);
await writeFile("test-results/import-evidence.json", JSON.stringify(saved, null, 2));
console.log(`Persisted ${saved.summary.total} Playwright results; all mapped to project ${fixture.projectId}.`);
