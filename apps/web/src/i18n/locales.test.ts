import { describe, expect, it } from "vitest";
import { isLocale, negotiateLocale } from "./locales";

describe("negotiateLocale", () => {
  it.each([
    [null, "de"],
    ["", "de"],
    ["en-US,en;q=0.9", "en"],
    ["de-DE,de;q=0.9,en;q=0.8", "de"],
    ["fr-FR,fr;q=0.9,en;q=0.5", "en"],
    ["fr-FR,es;q=0.9", "de"],
    ["en;q=0.4,de;q=0.6", "de"],
    ["de;q=0,en", "en"],
    ["EN-gb", "en"],
  ])("%s -> %s", (header, expected) => {
    expect(negotiateLocale(header)).toBe(expected);
  });
});

describe("isLocale", () => {
  it("accepts only supported locales", () => {
    expect(isLocale("de")).toBe(true);
    expect(isLocale("en")).toBe(true);
    expect(isLocale("fr")).toBe(false);
    expect(isLocale(undefined)).toBe(false);
  });
});
