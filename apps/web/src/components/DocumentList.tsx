import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import type { DocumentOut } from "@/api/client";
import { formatDate, formatMoney } from "./format";
import { StatusBadge } from "./StatusBadge";

type TypeKey = "pdf" | "xml" | "png" | "jpeg" | "other";

const TYPE_KEYS: Record<string, TypeKey> = {
  "application/pdf": "pdf",
  "application/xml": "xml",
  "image/png": "png",
  "image/jpeg": "jpeg",
};

export function DocumentList({ documents }: { documents: DocumentOut[] }) {
  const t = useTranslations("documents");
  const tInbox = useTranslations("inbox");
  const format = useFormatter();

  if (documents.length === 0) {
    return <p className="py-8 text-center text-slate-500">{tInbox("empty")}</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="border-b border-slate-200 text-slate-500">
        <tr>
          <th className="py-2 pr-4 font-medium">{t("name")}</th>
          <th className="py-2 pr-4 font-medium">{t("supplier")}</th>
          <th className="py-2 pr-4 font-medium">{t("number")}</th>
          <th className="py-2 pr-4 font-medium">{t("issueDate")}</th>
          <th className="py-2 pr-4 text-right font-medium">{t("amount")}</th>
          <th className="py-2 font-medium">{t("status")}</th>
        </tr>
      </thead>
      <tbody>
        {documents.map((doc) => {
          const summary = doc.summary;
          const counts = doc.finding_counts;
          return (
            <tr key={doc.id} className="border-b border-slate-100 align-top">
              <td className="max-w-56 py-2 pr-4">
                <Link
                  href={`/documents/${doc.id}`}
                  className="block truncate font-medium text-emerald-800 hover:underline"
                  title={doc.original_filename}
                >
                  {doc.original_filename}
                </Link>
                <span className="text-xs text-slate-500">
                  {t(`types.${TYPE_KEYS[doc.media_type] ?? "other"}`)}
                </span>
              </td>
              <td className="max-w-48 truncate py-2 pr-4">{summary?.seller_name ?? "–"}</td>
              <td className="py-2 pr-4">{summary?.number ?? "–"}</td>
              <td className="whitespace-nowrap py-2 pr-4">{formatDate(format, summary?.issue_date)}</td>
              <td className="whitespace-nowrap py-2 pr-4 text-right tabular-nums">
                {formatMoney(format, summary?.gross_total, summary?.currency)}
              </td>
              <td className="py-2">
                <StatusBadge status={doc.status} />
                <div className="mt-1 space-x-2 text-xs">
                  {counts.error > 0 && (
                    <span className="text-red-700">{t("errorCount", { count: counts.error })}</span>
                  )}
                  {counts.warning > 0 && (
                    <span className="text-amber-800">{t("warningCount", { count: counts.warning })}</span>
                  )}
                </div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
