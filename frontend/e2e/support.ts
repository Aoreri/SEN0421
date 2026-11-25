import { readFileSync } from "node:fs";
import { expect, type APIRequestContext, type Page } from "@playwright/test";

export type Fixture = {
  projectId: number;
  projectName: string;
  cases: { login: string; workflow: string; documents: string };
};
export const fixturePath = "test-results/fixture.json";
export const fixture = (): Fixture => JSON.parse(readFileSync(fixturePath, "utf8"));

export async function authenticate(api: APIRequestContext) {
  const response = await api.post("/api/auth/login", {
    data: { username: "admin", password: "demo1234" },
  });
  expect(response.status()).toBe(200);
  return { Authorization: `Bearer ${(await response.json()).access_token}` };
}

export async function login(page: Page, username = "admin") {
  await page.goto("/login");
  await page.getByLabel(/^Kullanıcı Adı(?: \*)?$/).fill(username);
  await page.getByLabel(/^Parola(?: \*)?$/).fill("demo1234");
  const response = page.waitForResponse(r => r.url().endsWith("/api/auth/login") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Giriş Yap", exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect(page.locator(".auth-user")).toContainText(username);
}
