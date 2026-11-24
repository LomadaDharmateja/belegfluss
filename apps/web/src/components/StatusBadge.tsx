import { useTranslations } from "next-intl";
import type { DocumentOut } from "@/api/client";

const STYLES: Record<DocumentOut["status"], string> = {
  received: "bg-slate-100 text-slate-700",
  processing: "bg-sky-50 text-sky-800",
  ready: "bg-emerald-50 text-emerald-800",
  needs_review: "bg-amber-50 text-amber-900",
  failed: "bg-red-50 text-red-800",
  approved: "bg-emerald-700 text-white",
};

export function StatusBadge({ status }: { status: DocumentOut["status"] }) {
  const t = useTranslations("documents");
  return (
    <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs ${STYLES[status]}`}>
      {t(`statusValues.${status}`)}
    </span>
  );
}
