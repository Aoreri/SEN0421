import { readFile } from "node:fs/promises";
import { test, expect } from "@playwright/test";
import { authenticate, fixture, login } from "./support";

test("login rejects an invalid password, persists a valid session and logs out", async ({ page }) => {
  test.info().annotations.push({ type: "test_case_id", description: fixture().cases.login });
  await page.goto("/login");
  await page.getByLabel(/^Kullanıcı Adı(?: \*)?$/).fill("tester");
  await page.getByLabel(/^Parola(?: \*)?$/).fill("incorrect");
  const denied = page.waitForResponse(r => r.url().endsWith("/api/auth/login") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Giriş Yap", exact: true }).click();
  expect((await denied).status()).toBe(401);
  await expect(page.locator(".auth-user")).toHaveCount(0);
  await login(page, "tester");
  await page.reload();
  await expect(page.locator(".auth-user")).toContainText("tester");
  await page.getByRole("button", { name: "Çıkış Yap", exact: true }).click();
  await page.reload();
  await expect(page.locator(".auth-user")).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.getItem("token"))).toBeNull();
});

test("test run, failed-execution defect and verified lifecycle survive reload", async ({ page, request }) => {
  const data = fixture();
  test.info().annotations.push({ type: "test_case_id", description: data.cases.workflow });
  const headers = await authenticate(request);
  await login(page);
  await page.goto("/test-runs");
  const runName = `${data.projectName} run`;
  await page.getByLabel(/^Koşum Adı(?: \*)?$/).fill(runName);
  await page.getByLabel(/^Proje(?: \*)?$/).selectOption(String(data.projectId));
  await page.getByRole("checkbox", { name: new RegExp(data.cases.workflow) }).check();
  const created = page.waitForResponse(r => r.url().endsWith("/api/test-runs") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Test Koşumu Başlat", exact: true }).click();
  const createdResponse = await created;
  expect(createdResponse.status()).toBe(201);
  const run = await createdResponse.json();
  expect(run.executions).toHaveLength(1);
  const executionId: number = run.executions[0].id;
  await expect(page.getByRole("heading", { name: `Aktif Koşum: #${run.id} · ${runName}`, exact: true })).toBeVisible();

  async function record(status: "Failed" | "Passed") {
    await page.getByLabel("Sonuç", { exact: true }).selectOption(status);
    await page.getByLabel("Gerçekleşen Sonuç", { exact: true }).fill(`PLN-34 ${status}`);
    const saved = page.waitForResponse(r => r.url().endsWith(`/executions/${executionId}`) && ["POST", "PUT"].includes(r.request().method()));
    await page.getByRole("button", { name: "Sonucu Kaydet", exact: true }).click();
    expect((await saved).status()).toBe(200);
  }
  await record("Failed");
  await page.getByRole("button", { name: "Başarısız Yürütmeden Defect Aç", exact: true }).click();
  await page.getByLabel(/^Defect Başlığı(?: \*)?$/).fill(`${data.projectName} defect`);
  const defectCreated = page.waitForResponse(r => r.url().endsWith(`/executions/${executionId}/defects`) && r.request().method() === "POST");
  await page.getByRole("button", { name: "Defect Oluştur & Bağla", exact: true }).click();
  const defectResponse = await defectCreated;
  expect(defectResponse.status()).toBe(201);
  const defectId: number = (await defectResponse.json()).id;
  const savedRun = await request.get(`/api/test-runs/${run.id}`, { headers });
  expect(savedRun.status()).toBe(200);
  expect((await savedRun.json()).executions[0]).toMatchObject({ status: "Failed", defect_ids: [defectId] });
  await page.goto(`/defects/${defectId}`);

  async function transition(from: string, to: string, status = 200) {
    const changed = page.waitForResponse(r => r.url().endsWith(`/defects/${defectId}/transition`) && r.request().method() === "POST");
    await page.getByRole("button", { name: `${from} → ${to}`, exact: true }).click();
    expect((await changed).status()).toBe(status);
  }
  await transition("Open", "In Progress");
  await transition("In Progress", "Resolved");
  await transition("Resolved", "Closed", 409); // failed execution cannot verify closure
  const before = await request.get(`/api/defects/${defectId}/history`, { headers });
  expect((await before.json()).map((e: { to: string }) => e.to)).toEqual(["Open", "In Progress", "Resolved"]);

  // Record a real successful verification in a new run; do not mutate test-case status.
  const verification = await request.post("/api/test-runs", {
    headers, data: { name: `${runName} verification`, project_id: data.projectId, test_case_ids: [data.cases.workflow] },
  });
  expect(verification.status()).toBe(201);
  const verificationRun = await verification.json();
  const verified = await request.post(`/api/test-runs/${verificationRun.id}/executions/${verificationRun.executions[0].id}`, {
    headers, data: { status: "Passed", actual_result: "PLN-34 verification", defect_ids: [defectId] },
  });
  expect(verified.status()).toBe(200);
  await page.reload();
  await transition("Resolved", "Closed");
  await transition("Closed", "Open");
  await page.reload();
  await expect(page.getByRole("list", { name: "Defect Değişiklik Geçmişi", exact: true }).getByRole("listitem")).toHaveCount(5);
  const history = await request.get(`/api/defects/${defectId}/history`, { headers });
  expect(history.status()).toBe(200);
  expect((await history.json()).map((e: { to: string }) => e.to)).toEqual(["Open", "In Progress", "Resolved", "Closed", "Open"]);
  await page.goto("/test-runs");
  await expect(page.getByRole("table", { name: "Test Koşum Geçmişi", exact: true })).toContainText(runName);
});

test("saved Test Plan snapshot exports HTML and downloads a PDF in the browser", async ({ page, request }) => {
  const data = fixture();
  test.info().annotations.push({ type: "test_case_id", description: data.cases.documents });
  const headers = await authenticate(request);
  const title = `${data.projectName} document`;
  const planResponse = await request.post("/api/test-plans", {
    headers, data: { project_id: data.projectId, version: "e2e-1", title, scope: "PLN-34 snapshot evidence" },
  });
  expect(planResponse.status()).toBe(201);
  const planId: number = (await planResponse.json()).id;
  const snapshot = await request.post(`/api/test-plans/${planId}/snapshots`, { headers });
  expect(snapshot.status()).toBe(201);
  const snapshotId: number = (await snapshot.json()).id;
  // Export the saved snapshot after editing the live plan to catch accidental live rendering.
  expect((await request.put(`/api/test-plans/${planId}`, {
    headers, data: { project_id: data.projectId, version: "e2e-2", title: "Changed after snapshot" },
  })).status()).toBe(200);
  await login(page);
  const html = await page.evaluate(async url => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } });
    if (!response.ok) throw new Error(`HTML export failed: ${response.status}`);
    return response.text();
  }, `/api/test-plans/${planId}/export?format=html&snapshot_id=${snapshotId}`);
  await page.setContent(html);
  await expect(page.locator("body")).toContainText(title);
  await expect(page.locator("body")).not.toContainText("Changed after snapshot");
  const downloadPromise = page.waitForEvent("download");
  // Fetch with the actual UI session; a direct link cannot send the JWT header.
  const blobURL = await page.evaluate(async url => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } });
    if (!response.ok) throw new Error(`PDF export failed: ${response.status}`);
    const filename = response.headers.get("content-disposition")?.match(/filename="([^"]+)"/)?.[1];
    if (!filename) throw new Error("Missing PDF filename");
    const objectURL = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = objectURL;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    return objectURL;
  }, `/api/test-plans/${planId}/export?format=pdf&snapshot_id=${snapshotId}`);
  const download = await downloadPromise;
  expect(await download.failure()).toBeNull();
  expect(download.suggestedFilename()).toBe(`test-plan-${planId}-e2e-1.pdf`);
  const path = await download.path();
  expect(path).not.toBeNull();
  const bytes = await readFile(path!);
  expect(bytes.subarray(0, 5).toString()).toBe("%PDF-");
  expect(bytes.toString("latin1")).toContain("%%EOF");
  await page.evaluate(url => URL.revokeObjectURL(url), blobURL);
});
