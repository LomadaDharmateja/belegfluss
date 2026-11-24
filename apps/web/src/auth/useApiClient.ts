"use client";

import { InteractionRequiredAuthError } from "@azure/msal-browser";
import { useMsal } from "@azure/msal-react";
import { useMemo } from "react";
import { createApiClient, type ApiClient } from "@/api/client";
import { useAuthConfig } from "./AuthProvider";

/** A typed API client that attaches a fresh access token for our API scope to every request. */
export function useApiClient(): ApiClient {
  const { instance } = useMsal();
  const config = useAuthConfig();

  return useMemo(
    () =>
      createApiClient(config.apiBaseUrl, async () => {
        const account = instance.getActiveAccount() ?? instance.getAllAccounts()[0];
        const request = { scopes: [config.apiScope], account };
        try {
          return (await instance.acquireTokenSilent(request)).accessToken;
        } catch (error) {
          if (error instanceof InteractionRequiredAuthError) {
            await instance.acquireTokenRedirect(request);
          }
          throw error;
        }
      }),
    [instance, config.apiBaseUrl, config.apiScope],
  );
}
