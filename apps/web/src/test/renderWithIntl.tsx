import { render, type RenderResult } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import de from "../../messages/de.json";
import en from "../../messages/en.json";

export function renderWithIntl(ui: ReactElement, locale: "de" | "en" = "en"): RenderResult {
  return render(
    <NextIntlClientProvider locale={locale} messages={locale === "de" ? de : en} timeZone="Europe/Berlin">
      {ui}
    </NextIntlClientProvider>,
  );
}
