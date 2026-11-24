export const locales = ["de", "en"] as const;
export type Locale = (typeof locales)[number];

const defaultLocale: Locale = "de";
export const LOCALE_COOKIE = "locale";

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (locales as readonly string[]).includes(value);
}

/**
 * Pick the first supported language from an Accept-Language header, in the user's order of
 * preference. Falls back to German (the product's home market).
 */
export function negotiateLocale(acceptLanguage: string | null | undefined): Locale {
  if (!acceptLanguage) return defaultLocale;
  const ranked = acceptLanguage
    .split(",")
    .map((part, index) => {
      const [tag, ...params] = part.trim().split(";");
      const q = params.map((p) => p.trim()).find((p) => p.startsWith("q="));
      const quality = q ? Number.parseFloat(q.slice(2)) : 1;
      return { language: tag.toLowerCase().split("-")[0], quality, index };
    })
    .filter((entry) => entry.language && !Number.isNaN(entry.quality) && entry.quality > 0)
    .sort((a, b) => b.quality - a.quality || a.index - b.index);
  const match = ranked.find((entry) => isLocale(entry.language));
  return match ? (match.language as Locale) : defaultLocale;
}
