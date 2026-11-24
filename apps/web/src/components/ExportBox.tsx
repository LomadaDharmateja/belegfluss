"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

/** Saves a Blob as a file through a temporary link (the request needs the bearer token). */
function saveFile(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement("a"), { href: url, download: name });
  link.click();
  URL.revokeObjectURL(url);
}

export function ExportBox({
  onExport,
}: {
  onExport: (period: { from: string; to: string }) => Promise<{ zip: Blob } | { code: string }>;
}) {
  const t = useTranslations("export");
  const tErrors = useTranslations("errors");
  const [period, setPeriod] = useState({ from: "", to: "" });
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setWorking(true);
    setError(null);
    const result = await onExport(period);
    setWorking(false);
    if ("zip" in result) {
      saveFile(result.zip, `belegfluss-export-${period.from || "start"}_${period.to || "today"}.zip`);
    } else {
      setError(tErrors.has(result.code as never) ? tErrors(result.code as never) : tErrors("generic"));
    }
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 text-sm">
      <h2 className="font-medium text-slate-800">{t("title")}</h2>
      <p className="mt-1 text-slate-600">{t("hint")}</p>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="block">
          <span className="text-slate-600">{t("from")}</span>
          <input
            type="date"
            value={period.from}
            onChange={(event) => setPeriod({ ...period, from: event.target.value })}
            className="mt-1 block rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="block">
          <span className="text-slate-600">{t("to")}</span>
          <input
            type="date"
            value={period.to}
            onChange={(event) => setPeriod({ ...period, to: event.target.value })}
            className="mt-1 block rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <button
          type="button"
          onClick={() => void download()}
          disabled={working}
          className="rounded-md bg-emerald-700 px-4 py-2 font-medium text-white disabled:opacity-50"
        >
          {working ? t("working") : t("download")}
        </button>
      </div>
      {error && (
        <p role="alert" className="mt-2 text-red-700">
          {error}
        </p>
      )}
    </section>
  );
}
