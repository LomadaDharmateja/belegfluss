"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { setLocale } from "@/i18n/actions";
import { locales } from "@/i18n/locales";

export function LanguageSwitch() {
  const t = useTranslations("languages");
  const current = useLocale();
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <div role="radiogroup" className="inline-flex rounded-md border border-slate-300 p-0.5">
      {locales.map((locale) => (
        <button
          key={locale}
          type="button"
          role="radio"
          aria-checked={locale === current}
          disabled={pending}
          lang={locale}
          onClick={() =>
            startTransition(async () => {
              await setLocale(locale);
              router.refresh();
            })
          }
          className={`rounded px-3 py-1.5 text-sm ${
            locale === current ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
          }`}
        >
          {t(locale)}
        </button>
      ))}
    </div>
  );
}
