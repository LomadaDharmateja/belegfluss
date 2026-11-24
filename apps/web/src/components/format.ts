import type { useFormatter } from "next-intl";

type Formatter = ReturnType<typeof useFormatter>;

/** Amounts arrive as exact decimal strings from the API; they are only formatted here, never computed with. */
export function formatMoney(
  format: Formatter,
  value: string | null | undefined,
  currency: string | null | undefined,
): string {
  if (value === null || value === undefined) return "–";
  const number = Number(value);
  try {
    return format.number(number, { style: "currency", currency: currency || "EUR" });
  } catch {
    // Unknown currency code in the invoice: show the plain number and the code.
    return `${format.number(number, { minimumFractionDigits: 2 })} ${currency ?? ""}`.trim();
  }
}

/** Invoice dates are calendar dates ("2026-11-18"), so they are shown without a time zone shift. */
export function formatDate(format: Formatter, value: string | null | undefined): string {
  if (!value) return "–";
  return format.dateTime(new Date(`${value}T00:00:00Z`), { dateStyle: "medium", timeZone: "UTC" });
}

export function formatQuantity(format: Formatter, value: string | null | undefined): string {
  return value === null || value === undefined ? "–" : format.number(Number(value));
}
