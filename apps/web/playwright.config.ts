import { defineConfig, devices } from "@playwright/test";

const PORT = 3100;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // Runs the production build (`pnpm build` first). Sign-in is not configured here on purpose:
  // these tests cover the public pages and language handling.
  webServer: {
    command: `next start --port ${PORT}`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    env: { ENTRA_CLIENT_ID: "", ENTRA_TENANT_SUBDOMAIN: "", ENTRA_TENANT_ID: "", ENTRA_API_SCOPE: "" },
  },
});
