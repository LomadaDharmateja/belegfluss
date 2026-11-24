"use client";

import { useMsal } from "@azure/msal-react";
import { useTranslations } from "next-intl";
import { useAuthConfig } from "@/auth/AuthProvider";

/** Only render inside MsalProvider (i.e. when useAuthReady() is true). */
export function SignInButton({ label }: { label: string }) {
  const { instance } = useMsal();
  const { apiScope } = useAuthConfig();
  return (
    <button
      type="button"
      className="rounded-md bg-emerald-700 px-4 py-2 font-medium text-white hover:bg-emerald-800"
      onClick={() => void instance.loginRedirect({ scopes: [apiScope] })}
    >
      {label}
    </button>
  );
}

export function SignOutButton() {
  const { instance } = useMsal();
  const t = useTranslations("nav");
  return (
    <button
      type="button"
      className="rounded-md px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100"
      onClick={() => void instance.logoutRedirect()}
    >
      {t("signOut")}
    </button>
  );
}
