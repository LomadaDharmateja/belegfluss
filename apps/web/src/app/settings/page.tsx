import { getTranslations } from "next-intl/server";
import { LanguageSwitch } from "@/components/LanguageSwitch";

export default async function SettingsPage() {
  const t = await getTranslations("settings");
  return (
    <section className="max-w-xl space-y-6">
      <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
      <div className="space-y-2">
        <h2 className="font-medium text-slate-800">{t("language")}</h2>
        <p className="text-sm text-slate-600">{t("languageHint")}</p>
        <LanguageSwitch />
      </div>
    </section>
  );
}
