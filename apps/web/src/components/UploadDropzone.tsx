"use client";

import { useFormatter, useTranslations } from "next-intl";
import { useId, useState, type DragEvent } from "react";
import type { UploadOutcome } from "@/api/client";
import { errorMessageKey } from "./errorMessage";

type Line = { id: number; tone: "info" | "ok" | "error"; text: string };

type Props = {
  maxBytes: number;
  upload: (file: File) => Promise<UploadOutcome>;
  onUploaded: () => void;
};

let nextLineId = 0;

export function UploadDropzone({ maxBytes, upload, onUploaded }: Props) {
  const t = useTranslations();
  const format = useFormatter();
  const inputId = useId();
  const [lines, setLines] = useState<Line[]>([]);
  const [dragging, setDragging] = useState(false);

  /** Adds a status line at the top and returns its id. */
  const say = (tone: Line["tone"], text: string) => {
    const id = nextLineId++;
    setLines((current) => [{ id, tone, text }, ...current].slice(0, 8));
    return id;
  };

  /** Replaces a line in place, e.g. "Uploading …" with the result. */
  const replace = (id: number, tone: Line["tone"], text: string) =>
    setLines((current) => current.map((line) => (line.id === id ? { id, tone, text } : line)));

  async function handleFiles(files: FileList | null) {
    if (!files) return;
    for (const file of Array.from(files)) {
      const name = file.name;
      if (file.size > maxBytes) {
        say("error", t("upload.failed", { name, reason: t("errors.upload.too_large") }));
        continue;
      }
      const lineId = say("info", t("upload.uploading", { name }));
      const outcome = await upload(file);
      if (outcome.kind === "added") replace(lineId, "ok", t("upload.done", { name }));
      else if (outcome.kind === "duplicate") replace(lineId, "ok", t("upload.duplicate", { name }));
      else {
        const key = errorMessageKey(outcome.code, (k) => t.has(k as never));
        replace(lineId, "error", t("upload.failed", { name, reason: t(key as never) }));
      }
    }
    onUploaded();
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    void handleFiles(event.dataTransfer.files);
  }

  const maxSize = format.number(maxBytes / (1024 * 1024), {
    style: "unit",
    unit: "megabyte",
    maximumFractionDigits: 0,
  });

  return (
    <div>
      <label
        htmlFor={inputId}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex cursor-pointer flex-col items-center rounded-lg border-2 border-dashed p-8 text-center ${
          dragging ? "border-emerald-600 bg-emerald-50" : "border-slate-300 bg-white"
        }`}
      >
        <span className="font-medium text-slate-800">{t("upload.hint")}</span>
        <span className="mt-2 text-sm text-slate-500">{t("upload.maxSize", { size: maxSize })}</span>
        <span className="mt-4 rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white">
          {t("upload.choose")}
        </span>
        <input
          id={inputId}
          type="file"
          multiple
          accept=".pdf,.xml,.png,.jpg,.jpeg,application/pdf,application/xml,text/xml,image/png,image/jpeg"
          className="sr-only"
          onChange={(event) => {
            void handleFiles(event.target.files);
            event.target.value = "";
          }}
        />
      </label>
      {lines.length > 0 && (
        <ul aria-live="polite" className="mt-3 space-y-1 text-sm">
          {lines.map((line) => (
            <li
              key={line.id}
              className={
                line.tone === "error"
                  ? "text-red-700"
                  : line.tone === "ok"
                    ? "text-emerald-800"
                    : "text-slate-600"
              }
            >
              {line.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
