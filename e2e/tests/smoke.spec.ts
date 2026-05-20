import { test, expect } from "@playwright/test";

test.describe("SIWZ-RAG Lite smoke", () => {
  test("home page loads with app title", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("SIWZ-RAG Lite")).toBeVisible();
    await expect(page.getByTestId("verify-textarea")).toBeVisible();
  });

  test("sidebar navigation visits all pages", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("nav-kb").click();
    await expect(page).toHaveURL(/\/kb\/?/);
    await expect(page.getByTestId("kb-start-btn")).toBeVisible();

    await page.getByTestId("nav-settings").click();
    await expect(page).toHaveURL(/\/settings\/?/);
    await expect(page.getByTestId("settings-llm-ollama")).toBeVisible();

    await page.getByTestId("nav-verify").click();
    await expect(page).toHaveURL(/\/(\?.*)?$/);
    await expect(page.getByTestId("verify-extract-btn")).toBeVisible();
  });

  test("locale switch in sidebar updates verify title", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Weryfikacja wymagań/i })).toBeVisible();
    await page.getByRole("button", { name: "en", exact: true }).click();
    await expect(page.getByRole("heading", { name: /Requirement verification/i })).toBeVisible();
  });
});

test.describe("Verify flow (heuristic, E2E mode)", () => {
  test("extract requirements from pasted text", async ({ page }) => {
    await page.goto("/");
    const sample = `
Wymagania:
- Dostawca musi zapewnić agenta EDR na Windows 10.
- System powinien wspierać integrację z SIEM.
`;
    await page.getByTestId("verify-textarea").fill(sample);
    await page.getByTestId("verify-extract-btn").click();
    await expect(page.getByTestId("verify-review")).toBeVisible({ timeout: 90_000 });
    await expect(page.locator("ul li").first()).toBeVisible();
  });
});

test.describe("Settings", () => {
  test("LLM provider shows Ollama selected by default", async ({ page }) => {
    await page.goto("/settings/");
    await expect(page.getByTestId("settings-llm-ollama")).toBeChecked();
  });
});

test.describe("API health", () => {
  test("backend health endpoint", async ({ request }) => {
    const res = await request.get("/api/health");
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe("ok");
  });
});
