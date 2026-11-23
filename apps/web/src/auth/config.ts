/**
 * Sign-in settings, read on the server at runtime (not baked into the build), so one image can
 * run in every environment. All values are public identifiers, no secrets (ADR-0003).
 */
export type AuthConfig = {
  configured: boolean;
  clientId: string;
  authority: string;
  apiScope: string;
  apiBaseUrl: string;
};

export function readAuthConfig(env: Record<string, string | undefined> = process.env): AuthConfig {
  const clientId = env.ENTRA_CLIENT_ID ?? "";
  const subdomain = env.ENTRA_TENANT_SUBDOMAIN ?? "";
  const apiScope = env.ENTRA_API_SCOPE ?? "";
  return {
    configured: Boolean(clientId && subdomain && apiScope),
    clientId,
    authority: subdomain ? `https://${subdomain}.ciamlogin.com/` : "",
    apiScope,
    apiBaseUrl: env.API_BASE_URL ?? "http://localhost:8000",
  };
}
