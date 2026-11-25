import { mkdirSync, writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { expect, request, type FullConfig } from "@playwright/test";
import { authenticate, fixturePath, type Fixture } from "./support";

export default async function setup(config: FullConfig) {
  // Explicit opt-in: these tests create records and must only target disposable SDS-06.
  if (process.env.E2E_DISPOSABLE !== "1") {
    throw new Error("Set E2E_DISPOSABLE=1 only for a disposable SDS-06 instance.");
  }
  const api = await request.newContext({ baseURL: config.projects[0].use.baseURL });
  try {
    expect((await api.get("/api/health")).status()).toBe(200);
    const headers = await authenticate(api);
    const suffix = randomUUID().slice(0, 8);
    const projectName = `PLN-34 E2E ${suffix}`;
    const project = await api.post("/api/projects", { headers, data: { name: projectName } });
    expect(project.status()).toBe(201);
    const projectId: number = (await project.json()).id;
    const requirementId = `P34-${suffix}`;
    expect((await api.post("/api/requirements", {
      headers, data: { id: requirementId, project_id: projectId, title: "PLN-34 E2E acceptance" },
    })).status()).toBe(201);
    const cases = { login: `P34-${suffix}-L`, workflow: `P34-${suffix}-W`, documents: `P34-${suffix}-D` };
    for (const [name, id] of Object.entries(cases)) {
      expect((await api.post("/api/test-cases", {
        headers, data: { id, title: `PLN-34 ${name}`, requirements: [requirementId], automated: true },
      })).status()).toBe(201);
    }
    mkdirSync("test-results", { recursive: true });
    const data: Fixture = { projectId, projectName, cases };
    writeFileSync(fixturePath, JSON.stringify(data, null, 2));
  } finally {
    await api.dispose();
  }
}
