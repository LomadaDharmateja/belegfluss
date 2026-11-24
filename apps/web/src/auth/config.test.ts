import { describe, expect, it } from "vitest";
import { readAuthConfig } from "./config";

const TENANT_ID = "3a35c9ff-f06d-401b-913a-e4443de51401";

const fullEnv = {
  ENTRA_CLIENT_ID: "spa-id",
  ENTRA_TENANT_SUBDOMAIN: "belegflussdev",
  ENTRA_TENANT_ID: TENANT_ID,
  ENTRA_API_SCOPE: "api://api-id/access_as_user",
  API_BASE_URL: "https://api.example",
};

describe("readAuthConfig", () => {
  it("is not configured without tenant values", () => {
    const config = readAuthConfig({});
    expect(config.configured).toBe(false);
    expect(config.apiBaseUrl).toBe("http://localhost:8000");
  });

  it("is not configured without the tenant ID", () => {
    const config = readAuthConfig({ ...fullEnv, ENTRA_TENANT_ID: "" });
    expect(config.configured).toBe(false);
  });

  it("builds the External ID authority from the tenant subdomain", () => {
    expect(readAuthConfig(fullEnv)).toEqual({
      configured: true,
      clientId: "spa-id",
      authority: "https://belegflussdev.ciamlogin.com/",
      knownAuthorities: ["belegflussdev.ciamlogin.com", `${TENANT_ID}.ciamlogin.com`],
      apiScope: "api://api-id/access_as_user",
      apiBaseUrl: "https://api.example",
    });
  });

  // Regression: the tenant's discovery document names a tenant-ID-based issuer
  // (https://<tenant-id>.ciamlogin.com/<tenant-id>/v2.0). MSAL rejects it unless that host is a
  // known authority, and sign-in stopped with "endpoints_resolution_error".
  it("trusts the tenant-ID-based issuer host", () => {
    const issuer = `https://${TENANT_ID}.ciamlogin.com/${TENANT_ID}/v2.0`;
    expect(readAuthConfig(fullEnv).knownAuthorities).toContain(new URL(issuer).host);
  });
});
