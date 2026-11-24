"use client";

import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import type { DocumentOut } from "@/api/client";

/**
 * Approve a checked document for the export, or reopen an approved one.
 * With open errors the person must tick that they have seen them (ADR-0017).
 */
export function ApprovalBox({
  document,
  onApprove,
  onReopen,
}: {
  document: DocumentOut;
  onApprove: (acknowledgeErrors: boolean) => Promise<string | null>;
  onReopen: () => Promise<string | null>;
}) {
  const t = useTranslations("approval");
  const tErrors = useTranslations("errors");
  const format = useFormatter();
  const [acknowledged, setAcknowledged] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasErrors = document.finding_counts.error > 0;
  const approved = document.status === "approved";

  async function run(action: () => Promise<string | null>) {
    const code = await action();
    setError(code ? (tErrors.has(code as never) ? tErrors(code as never) : tErrors("generic")) : null);
  }

  return (
    <div className="space-y-3 rounded-md border border-slate-200 bg-white p-4 text-sm">
      <h2 className="font-medium text-slate-800">{t("title")}</h2>
      {approved ? (
        <>
          <p>
            {t("approvedOn", {
              date: format.dateTime(new Date(document.approved_at ?? document.created_at), {
                dateStyle: "medium",
                timeStyle: "short",
              }),
            })}
          </p>
          <button
            type="button"
            onClick={() => void run(onReopen)}
            className="rounded-md border border-slate-300 px-3 py-1.5"
          >
            {t("reopen")}
          </button>
        </>
      ) : (
        <>
          <p className="text-slate-600">{t("hint")}</p>
          {hasErrors && (
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={acknowledged}
                onChange={(event) => setAcknowledged(event.target.checked)}
                className="mt-0.5"
              />
              <span>{t("acknowledge")}</span>
            </label>
          )}
          <button
            type="button"
            disabled={hasErrors && !acknowledged}
            onClick={() => void run(() => onApprove(hasErrors && acknowledged))}
            className="rounded-md bg-emerald-700 px-4 py-2 font-medium text-white disabled:opacity-50"
          >
            {t("approve")}
          </button>
        </>
      )}
      {error && (
        <p role="alert" className="text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
