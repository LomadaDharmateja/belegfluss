import { describe, expect, it } from "vitest";
import { readAuthConfig } from "./config";

describe("readAuthConfig", () => {
  it("is not configured without tenant values", () => {
    const config = readAuthConfig({});
    expect(config.configured).toBe(false);
    expect(config.apiBaseUrl).toBe("http://localhost:8000");
  });

  it("builds the External ID authority from the tenant subdomain", () => {
    const config = readAuthConfig({
      ENTRA_CLIENT_ID: "spa-id",
      ENTRA_TENANT_SUBDOMAIN: "belegflussdev",
      ENTRA_API_SCOPE: "api://api-id/access_as_user",
      API_BASE_URL: "https://api.example",
    });
    expect(config).toEqual({
      configured: true,
      clientId: "spa-id",
      authority: "https://belegflussdev.ciamlogin.com/",
      apiScope: "api://api-id/access_as_user",
      apiBaseUrl: "https://api.example",
    });
  });
});
