"use client";

import { AuthenticatedTemplate, UnauthenticatedTemplate } from "@azure/msal-react";
import { useTranslations } from "next-intl";
import { useAuthConfig, useAuthReady } from "@/auth/AuthProvider";
import { DocumentDetail } from "@/components/DocumentDetail";
import { Landing } from "@/components/Landing";
import { SignInButton } from "@/components/SignInButton";

export function DocumentPage({ documentId }: { documentId: string }) {
  const { configured } = useAuthConfig();
  const ready = useAuthReady();
  const t = useTranslations();

  if (!configured) return <Landing signIn={null} />;
  if (!ready) return <p className="py-12 text-slate-500">{t("app.loading")}</p>;
  return (
    <>
      <AuthenticatedTemplate>
        <DocumentDetail documentId={documentId} />
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <Landing signIn={<SignInButton label={t("landing.signIn")} />} />
      </UnauthenticatedTemplate>
    </>
  );
}
