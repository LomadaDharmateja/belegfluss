import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages, getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { AuthProvider } from "@/auth/AuthProvider";
import { readAuthConfig } from "@/auth/config";
import { Header } from "@/components/Header";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("app");
  return { title: `${t("name")} · ${t("tagline")}` };
}

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();
  // Read at request time on the server, so the same build works in every environment.
  const authConfig = readAuthConfig();

  return (
    <html lang={locale}>
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <AuthProvider config={authConfig}>
            <Header />
            <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
          </AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
