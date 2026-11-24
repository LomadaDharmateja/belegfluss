import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import type { FindingOut } from "@/api/client";

const SEVERITY_STYLES: Record<FindingOut["severity"], string> = {
  error: "border-red-200 bg-red-50 text-red-900",
  warning: "border-amber-200 bg-amber-50 text-amber-950",
  info: "border-slate-200 bg-slate-50 text-slate-800",
};

// Parameters that are amounts: formatted in the user's language (447.40 -> 447,40 in German).
const AMOUNT_PARAMS = new Set(["expected", "actual", "amount"]);

/**
 * One line per finding. Belegfluss codes and curated official rules have a plain-language text
 * (messages: findings.codes.*); other official rules fall back to the validator's rule text.
 * Everything is rendered as text, never as HTML.
 */
export function FindingsList({ findings }: { findings: FindingOut[] }) {
  const t = useTranslations("findings");
  const format = useFormatter();

  const params = (finding: FindingOut) =>
    Object.fromEntries(
      Object.entries(finding.params).map(([name, value]) => [
        name,
        AMOUNT_PARAMS.has(name)
          ? format.number(Number(value), { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          : value,
      ]),
    );

  return (
    <ul className="space-y-2">
      {findings.map((finding) => {
        const key = `codes.${finding.code}`;
        const explained = t.has(key as never);
        const otherDocument = finding.code === "BF-DUPLICATE" ? finding.params.document_id : undefined;
        return (
          <li key={finding.id} className={`rounded-md border p-3 text-sm ${SEVERITY_STYLES[finding.severity]}`}>
            <div className="flex flex-wrap items-baseline gap-x-2">
              <span className="font-semibold">{t(`severity.${finding.severity}`)}</span>
              <span className="font-mono text-xs opacity-70">{finding.code}</span>
            </div>
            <p className="mt-1">
              {explained ? t(key as never, params(finding) as never) : (finding.message ?? finding.code)}
            </p>
            {otherDocument && (
              <Link href={`/documents/${otherDocument}`} className="mt-1 inline-block underline">
                {t("openOther")}
              </Link>
            )}
            {explained && finding.message && (
              <details className="mt-1 text-xs opacity-80">
                <summary className="cursor-pointer">{t("officialText")}</summary>
                <p className="mt-1">{finding.message}</p>
              </details>
            )}
            {finding.business_terms.length > 0 && (
              <p className="mt-1 text-xs opacity-70">
                {t("fields", { terms: finding.business_terms.join(", ") })}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
