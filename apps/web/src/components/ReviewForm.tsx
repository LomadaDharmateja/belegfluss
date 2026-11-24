"use client";

import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import type { FindingOut, InvoiceCorrection, InvoiceModel } from "@/api/client";

type FieldName = keyof InvoiceCorrection & string;

const FIELDS: { name: FieldName; kind: "text" | "date" | "amount" }[] = [
  { name: "seller_name", kind: "text" },
  { name: "seller_vat_id", kind: "text" },
  { name: "number", kind: "text" },
  { name: "issue_date", kind: "date" },
  { name: "due_date", kind: "date" },
  { name: "currency", kind: "text" },
  { name: "iban", kind: "text" },
  { name: "net", kind: "amount" },
  { name: "vat", kind: "amount" },
  { name: "gross", kind: "amount" },
  { name: "due", kind: "amount" },
];

/** Current values of the correctable fields, as form strings ("" = empty). */
export function initialValues(model: InvoiceModel): Record<FieldName, string> {
  return {
    seller_name: model.seller?.name ?? "",
    seller_vat_id: model.seller?.vat_id ?? "",
    number: model.number ?? "",
    issue_date: model.issue_date ?? "",
    due_date: model.due_date ?? "",
    currency: model.currency ?? "",
    iban: model.ibans?.[0] ?? "",
    net: model.totals?.net ?? "",
    vat: model.totals?.vat ?? "",
    gross: model.totals?.gross ?? "",
    due: model.totals?.due ?? "",
  };
}

/** Only changed fields are sent. Amounts accept a decimal comma; empty clears a value. */
export function changedFields(
  before: Record<FieldName, string>,
  after: Record<FieldName, string>,
): InvoiceCorrection {
  const correction: Record<string, string | null> = {};
  for (const { name, kind } of FIELDS) {
    const typed = after[name].trim();
    const value = kind === "amount" ? typed.replace(",", ".") : typed;
    if (value === before[name]) continue; // "447,40" is the same as "447.40"
    correction[name] = value === "" ? null : value;
  }
  return correction as InvoiceCorrection;
}

// Findings that point at a field the person should look at.
const UNCERTAIN: Record<string, FieldName | undefined> = {
  number: "number",
  vat_id: "seller_vat_id",
  iban: "iban",
  gross: "gross",
  issue_date: "issue_date",
  due_date: "due_date",
};

export function uncertainFields(findings: FindingOut[]): Set<FieldName> {
  const fields = new Set<FieldName>();
  for (const finding of findings) {
    const named = UNCERTAIN[finding.params.field ?? ""];
    if (named) fields.add(named);
    if (finding.code === "BF-AI-INVALID-IBAN") fields.add("iban");
    if (finding.code === "BF-AI-INVALID-VAT-ID") fields.add("seller_vat_id");
    if (finding.code === "BF-TOTAL-GROSS") fields.add("gross");
  }
  return fields;
}

export function ReviewForm({
  model,
  findings,
  onSave,
}: {
  model: InvoiceModel;
  findings: FindingOut[];
  onSave: (correction: InvoiceCorrection) => Promise<string | null>;
}) {
  const t = useTranslations("review");
  const tErrors = useTranslations("errors");
  const before = initialValues(model);
  const [values, setValues] = useState(before);
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const uncertain = uncertainFields(findings);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const correction = changedFields(before, values);
    if (Object.keys(correction).length === 0) {
      setMessage({ tone: "ok", text: t("nothingChanged") });
      return;
    }
    const error = await onSave(correction);
    setMessage(
      error
        ? { tone: "error", text: tErrors.has(error as never) ? tErrors(error as never) : tErrors("generic") }
        : { tone: "ok", text: t("saved") },
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-md border border-sky-200 bg-sky-50 p-4">
      <div>
        <h2 className="font-medium text-slate-800">{t("title")}</h2>
        <p className="text-sm text-slate-600">{t("hint")}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {FIELDS.map(({ name, kind }) => (
          <label key={name} className="block text-sm">
            <span className="text-slate-600">{t(`fields.${name}`)}</span>
            <input
              name={name}
              type={kind === "date" ? "date" : "text"}
              inputMode={kind === "amount" ? "decimal" : undefined}
              value={values[name]}
              onChange={(event) => setValues({ ...values, [name]: event.target.value })}
              aria-invalid={uncertain.has(name) || undefined}
              className={`mt-1 block w-full rounded border px-2 py-1 ${
                uncertain.has(name) ? "border-amber-500 bg-amber-50" : "border-slate-300 bg-white"
              }`}
            />
          </label>
        ))}
      </div>
      <div className="flex items-center gap-3">
        <button type="submit" className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white">
          {t("save")}
        </button>
        {message && (
          <p role="status" className={message.tone === "error" ? "text-sm text-red-700" : "text-sm text-emerald-800"}>
            {message.text}
          </p>
        )}
      </div>
    </form>
  );
}
