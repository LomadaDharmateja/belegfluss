"use client";

import { AuthenticatedTemplate } from "@azure/msal-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useAuthReady } from "@/auth/AuthProvider";
import { SignOutButton } from "./SignInButton";

export function Header() {
  const t = useTranslations();
  const ready = useAuthReady();
  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-5xl items-center gap-6 px-6 py-3">
        <Link href="/" className="font-semibold text-slate-900">
          {t("app.name")}
        </Link>
        <Link href="/" className="text-sm text-slate-600 hover:text-slate-900">
          {t("nav.inbox")}
        </Link>
        <Link href="/settings" className="text-sm text-slate-600 hover:text-slate-900">
          {t("nav.settings")}
        </Link>
        <div className="ml-auto">
          {ready && (
            <AuthenticatedTemplate>
              <SignOutButton />
            </AuthenticatedTemplate>
          )}
        </div>
      </nav>
    </header>
  );
}
