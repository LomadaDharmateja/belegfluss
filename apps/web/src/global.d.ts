import type messages from "../messages/en.json";
import type { locales } from "./i18n/locales";

// Type-checked message keys and locales for next-intl (ADR-0010).
declare module "next-intl" {
  interface AppConfig {
    Locale: (typeof locales)[number];
    Messages: typeof messages;
  }
}
