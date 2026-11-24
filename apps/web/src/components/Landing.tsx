import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

/** Public start page. `signIn` is the sign-in button, or null if sign-in isn't configured. */
export function Landing({ signIn }: { signIn: ReactNode | null }) {
  const t = useTranslations("landing");
  return (
    <section className="mx-auto max-w-2xl py-12">
      <h1 className="text-3xl font-semibold tracking-tight text-slate-900">{t("title")}</h1>
      <p className="mt-4 text-lg text-slate-600">{t("subtitle")}</p>
      <ul className="mt-8 space-y-2 text-slate-700">
        <li>✓ {t("pointCollect")}</li>
        <li>✓ {t("pointCheck")}</li>
        <li>✓ {t("pointHandoff")}</li>
      </ul>
      <div className="mt-10">
        {signIn ? (
          <>
            {signIn}
            <p className="mt-3 text-sm text-slate-500">{t("signInHint")}</p>
          </>
        ) : (
          <p role="status" className="rounded-md bg-amber-50 p-3 text-sm text-amber-900">
            {t("notConfigured")}
          </p>
        )}
      </div>
    </section>
  );
}
