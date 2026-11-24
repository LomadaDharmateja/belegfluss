import { describe, expect, it } from "vitest";
import de from "../../messages/de.json";
import en from "../../messages/en.json";

function flatten(value: unknown, prefix = ""): Record<string, string> {
  if (typeof value === "string") return { [prefix]: value };
  return Object.entries(value as Record<string, unknown>).reduce<Record<string, string>>(
    (acc, [key, child]) => ({ ...acc, ...flatten(child, prefix ? `${prefix}.${key}` : key) }),
    {},
  );
}

describe("translations", () => {
  const deKeys = flatten(de);
  const enKeys = flatten(en);

  it("German and English have exactly the same keys", () => {
    expect(Object.keys(deKeys).sort()).toEqual(Object.keys(enKeys).sort());
  });

  it("no translation is empty", () => {
    const empty = Object.entries({ ...deKeys, ...enKeys }).filter(([, text]) => !text.trim());
    expect(empty).toEqual([]);
  });

  it("placeholders match between languages", () => {
    // ICU arguments: "{name}" or "{count, plural, ...}" (not words inside plural branches).
    const placeholders = (text: string) =>
      [...text.matchAll(/\{(\w+)\s*[,}]/g)].map((m) => m[1]).sort();
    for (const key of Object.keys(enKeys)) {
      expect(placeholders(deKeys[key]), key).toEqual(placeholders(enKeys[key]));
    }
  });

  it("every API error code used by the server has a message", () => {
    const serverCodes = [
      "upload.too_large",
      "upload.unsupported_type",
      "upload.empty",
      "auth.missing_token",
      "auth.invalid_token",
      "auth.token_expired",
      "auth.insufficient_scope",
      "auth.not_configured",
      "org.not_found",
      "document.not_found",
    ];
    for (const code of serverCodes) {
      expect(enKeys[`errors.${code}`], code).toBeTruthy();
    }
  });
});
