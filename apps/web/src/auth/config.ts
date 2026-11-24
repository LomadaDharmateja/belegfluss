/**
 * Sign-in settings, read on the server at runtime (not baked into the build), so one image can
 * run in every environment. All values are public identifiers, no secrets (ADR-0003).
 */
export type AuthConfig = {
  configured: boolean;
  clientId: string;
  authority: string;
  /** Hosts MSAL may trust: the sign-in host and the host of the tenant's issuer. */
  knownAuthorities: string[];
  apiScope: string;
  apiBaseUrl: string;
};

export function readAuthConfig(env: Record<string, string | undefined> = process.env): AuthConfig {
  const clientId = env.ENTRA_CLIENT_ID ?? "";
  const subdomain = env.ENTRA_TENANT_SUBDOMAIN ?? "";
  const tenantId = env.ENTRA_TENANT_ID ?? "";
  const apiScope = env.ENTRA_API_SCOPE ?? "";
  const configured = Boolean(clientId && subdomain && tenantId && apiScope);
  return {
    configured,
    clientId,
    authority: subdomain ? `https://${subdomain}.ciamlogin.com/` : "",
    // The tenant's discovery document names its issuer as https://<tenant-id>.ciamlogin.com/...
    // MSAL only accepts an issuer host that differs from the sign-in host if it is listed here.
    knownAuthorities: configured ? [`${subdomain}.ciamlogin.com`, `${tenantId}.ciamlogin.com`] : [],
    apiScope,
    apiBaseUrl: env.API_BASE_URL ?? "http://localhost:8000",
  };
}
