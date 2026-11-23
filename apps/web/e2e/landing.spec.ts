import { expect, test } from "@playwright/test";

test.describe("language handling", () => {
  test("German browser gets the German landing page", async ({ browser }) => {
    const context = await browser.newContext({ locale: "de-DE" });
    const page = await context.newPage();
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "de");
    await expect(
      page.getByRole("heading", { name: "Alle eingehenden Rechnungen an einem Ort" }),
    ).toBeVisible();
    await context.close();
  });

  test("English browser gets the English landing page", async ({ browser }) => {
    const context = await browser.newContext({ locale: "en-GB" });
    const page = await context.newPage();
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(
      page.getByRole("heading", { name: "All your incoming invoices in one place" }),
    ).toBeVisible();
    await context.close();
  });

  test("the language switch changes the language and remembers it", async ({ browser }) => {
    const context = await browser.newContext({ locale: "en-GB" });
    const page = await context.newPage();
    await page.goto("/settings");
    await page.getByRole("radio", { name: "Deutsch" }).click();
    await expect(page.getByRole("heading", { name: "Einstellungen" })).toBeVisible();

    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Alle eingehenden Rechnungen an einem Ort" }),
    ).toBeVisible();
    await context.close();
  });
});

test("without tenant settings the page says sign-in is not configured", async ({ browser }) => {
  const context = await browser.newContext({ locale: "en-GB" });
  const page = await context.newPage();
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText(
    "Sign-in is not configured in this environment yet.",
  );
  await context.close();
});

test("security headers are set", async ({ request }) => {
  const response = await request.get("/");
  expect(response.headers()["x-content-type-options"]).toBe("nosniff");
  expect(response.headers()["x-frame-options"]).toBe("DENY");
  expect(response.headers()["x-powered-by"]).toBeUndefined();
});
