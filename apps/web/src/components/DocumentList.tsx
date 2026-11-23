import { useFormatter, useTranslations } from "next-intl";
import type { DocumentOut } from "@/api/client";

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
          <th className="py-2 pr-4 font-medium">{t("type")}</th>
          <th className="py-2 pr-4 text-right font-medium">{t("size")}</th>
          <th className="py-2 pr-4 font-medium">{t("uploaded")}</th>
          <th className="py-2 font-medium">{t("status")}</th>
        </tr>
      </thead>
      <tbody>
        {documents.map((doc) => (
          <tr key={doc.id} className="border-b border-slate-100">
            <td className="max-w-xs truncate py-2 pr-4" title={doc.original_filename}>
              {doc.original_filename}
            </td>
            <td className="py-2 pr-4">{t(`types.${TYPE_KEYS[doc.media_type] ?? "other"}`)}</td>
            <td className="py-2 pr-4 text-right tabular-nums">
              {format.number(doc.size_bytes / 1024, {
                style: "unit",
                unit: "kilobyte",
                maximumFractionDigits: 1,
              })}
            </td>
            <td className="py-2 pr-4">
              {format.dateTime(new Date(doc.created_at), { dateStyle: "medium", timeStyle: "short" })}
            </td>
            <td className="py-2">
              <span className="rounded-full bg-sky-50 px-2 py-0.5 text-xs text-sky-800">
                {t(`statusValues.${doc.status}`)}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
