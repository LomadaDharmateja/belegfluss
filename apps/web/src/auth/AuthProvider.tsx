"use client";

import {
  EventType,
  PublicClientApplication,
  type AuthenticationResult,
  type EventMessage,
} from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { createContext, useContext, useSyncExternalStore, type ReactNode } from "react";
import type { AuthConfig } from "./config";

type AuthState = { config: AuthConfig; ready: boolean };

const AuthStateContext = createContext<AuthState | null>(null);

function useAuthState(): AuthState {
  const state = useContext(AuthStateContext);
  if (!state) throw new Error("Auth hooks must be used inside <AuthProvider>");
  return state;
}

export function useAuthConfig(): AuthConfig {
  return useAuthState().config;
}

/** True once the MSAL client exists in the browser. MSAL hooks may only be used after that. */
export function useAuthReady(): boolean {
  return useAuthState().ready;
}

function createMsal(config: AuthConfig): PublicClientApplication {
  const instance = new PublicClientApplication({
    auth: {
      clientId: config.clientId,
      authority: config.authority,
      knownAuthorities: [new URL(config.authority).host],
      redirectUri: window.location.origin,
      postLogoutRedirectUri: window.location.origin,
    },
    // Session storage: tokens are gone when the tab closes.
    cache: { cacheLocation: "sessionStorage" },
  });
  instance.addEventCallback((event: EventMessage) => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
      instance.setActiveAccount((event.payload as AuthenticationResult).account);
    }
  });
  return instance;
}

// One MSAL client per browser tab (re-created only if the configuration changes).
let cached: { key: string; instance: PublicClientApplication } | null = null;

function getMsal(config: AuthConfig): PublicClientApplication {
  const key = `${config.clientId}|${config.authority}`;
  if (cached?.key !== key) cached = { key, instance: createMsal(config) };
  return cached.instance;
}

const noop = () => () => {};

/** false during server rendering and hydration, true afterwards in the browser. */
function useIsBrowser(): boolean {
  return useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
}

/**
 * MSAL runs only in the browser, so the client is created after hydration (server and first
 * browser render match). MsalProvider itself calls initialize() and handles the redirect back from
 * the sign-in page (checked in the @azure/msal-react 5.8 source).
 */
export function AuthProvider({ config, children }: { config: AuthConfig; children: ReactNode }) {
  const isBrowser = useIsBrowser();
  const msal = isBrowser && config.configured ? getMsal(config) : null;
  const state: AuthState = { config, ready: msal !== null };
  return (
    <AuthStateContext.Provider value={state}>
      {msal ? <MsalProvider instance={msal}>{children}</MsalProvider> : children}
    </AuthStateContext.Provider>
  );
}
