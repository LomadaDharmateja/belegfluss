import { useFormatter, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import type { InvoiceModel, InvoiceOut } from "@/api/client";
import { formatDate, formatMoney, formatQuantity } from "./format";

type Party = InvoiceModel["seller"];

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-slate-900">{children}</dd>
    </div>
  );
}

function PartyCard({ title, party }: { title: string; party: Party }) {
  const t = useTranslations("detail");
  const address = party?.address;
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">{title}</h3>
      <p className="font-medium text-slate-900">{party?.name ?? "–"}</p>
      {address?.line1 && <p>{address.line1}</p>}
      {address?.line2 && <p>{address.line2}</p>}
      {(address?.post_code || address?.city) && (
        <p>{[address?.post_code, address?.city].filter(Boolean).join(" ")}</p>
      )}
      {address?.country_code && <p>{address.country_code}</p>}
      {party?.vat_id && <p className="mt-2 text-sm">{`${t("vatId")}: ${party.vat_id}`}</p>}
      {party?.tax_number && <p className="text-sm">{`${t("taxNumber")}: ${party.tax_number}`}</p>}
    </div>
  );
}

/** The read invoice, rendered as text from our model (never HTML from the invoice). */
export function InvoiceView({ invoice }: { invoice: InvoiceOut }) {
  const t = useTranslations("detail");
  const format = useFormatter();
  const model = invoice.model;
  const money = (value: string | null | undefined) => formatMoney(format, value, model.currency);
  const totals = model.totals;
  const totalRows: [string, string | null | undefined][] = [
    ["lineNet", totals?.line_net],
    ["allowances", totals?.allowances],
    ["charges", totals?.charges],
    ["totalNet", totals?.net],
    ["totalVat", totals?.vat],
    ["totalGross", totals?.gross],
    ["paid", totals?.paid],
    ["rounding", totals?.rounding],
    ["due", totals?.due],
  ];

  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Field label={t("format")}>
          {t(`sourceValues.${invoice.source}`)}
          {invoice.syntax && <span className="block text-xs text-slate-500">{t(`syntaxValues.${invoice.syntax}`)}</span>}
        </Field>
        <Field label={t("number")}>{model.number ?? "–"}</Field>
        <Field label={t("issueDate")}>{formatDate(format, model.issue_date)}</Field>
        <Field label={t("dueDate")}>{formatDate(format, model.due_date)}</Field>
        {model.delivery_date && <Field label={t("deliveryDate")}>{formatDate(format, model.delivery_date)}</Field>}
        {(model.period_start || model.period_end) && (
          <Field label={t("period")}>
            {`${formatDate(format, model.period_start)} – ${formatDate(format, model.period_end)}`}
          </Field>
        )}
        {model.buyer_reference && <Field label={t("buyerReference")}>{model.buyer_reference}</Field>}
      </dl>

      <div className="grid gap-4 sm:grid-cols-2">
        <PartyCard title={t("seller")} party={model.seller} />
        <PartyCard title={t("buyer")} party={model.buyer} />
      </div>

      {(model.lines ?? []).length > 0 && (
        <section>
          <h3 className="mb-2 font-medium text-slate-800">{t("lines")}</h3>
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-slate-500">
              <tr>
                <th className="py-1 pr-3 font-medium">{t("item")}</th>
                <th className="py-1 pr-3 text-right font-medium">{t("quantity")}</th>
                <th className="py-1 pr-3 text-right font-medium">{t("unitPrice")}</th>
                <th className="py-1 pr-3 text-right font-medium">{t("vatRate")}</th>
                <th className="py-1 text-right font-medium">{t("net")}</th>
              </tr>
            </thead>
            <tbody>
              {(model.lines ?? []).map((line, index) => (
                <tr key={`${line.id ?? ""}-${index}`} className="border-b border-slate-100">
                  <td className="py-1 pr-3">{line.name ?? "–"}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">
                    {`${formatQuantity(format, line.quantity)} ${line.unit ?? ""}`.trim()}
                  </td>
                  <td className="py-1 pr-3 text-right tabular-nums">{money(line.unit_price)}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">
                    {line.vat_rate === null || line.vat_rate === undefined ? "–" : `${formatQuantity(format, line.vat_rate)} %`}
                  </td>
                  <td className="py-1 text-right tabular-nums">{money(line.net_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <div className="grid gap-6 sm:grid-cols-2">
        {(model.vat_breakdown ?? []).length > 0 && (
          <section>
            <h3 className="mb-2 font-medium text-slate-800">{t("vatBreakdown")}</h3>
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500">
                <tr>
                  <th className="py-1 pr-3 font-medium">{t("category")}</th>
                  <th className="py-1 pr-3 text-right font-medium">{t("taxable")}</th>
                  <th className="py-1 text-right font-medium">{t("tax")}</th>
                </tr>
              </thead>
              <tbody>
                {(model.vat_breakdown ?? []).map((vat, index) => (
                  <tr key={index} className="border-b border-slate-100">
                    <td className="py-1 pr-3">
                      {`${vat.category ?? "–"}${vat.rate !== null && vat.rate !== undefined ? ` · ${formatQuantity(format, vat.rate)} %` : ""}`}
                      {vat.exemption_reason && <span className="block text-xs text-slate-500">{vat.exemption_reason}</span>}
                    </td>
                    <td className="py-1 pr-3 text-right tabular-nums">{money(vat.taxable_amount)}</td>
                    <td className="py-1 text-right tabular-nums">{money(vat.tax_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
        <section>
          <h3 className="mb-2 font-medium text-slate-800">{t("totals")}</h3>
          <dl className="space-y-1 text-sm">
            {totalRows
              .filter(([, value]) => value !== null && value !== undefined)
              .map(([label, value]) => (
                <div
                  key={label}
                  className={`flex justify-between ${label === "due" ? "border-t border-slate-200 pt-1 font-semibold" : ""}`}
                >
                  <dt>{t(label as never)}</dt>
                  <dd className="tabular-nums">{money(value)}</dd>
                </div>
              ))}
          </dl>
        </section>
      </div>

      {((model.ibans ?? []).length > 0 || model.payment_terms) && (
        <dl className="grid gap-4 sm:grid-cols-2">
          {(model.ibans ?? []).length > 0 && <Field label={t("iban")}>{(model.ibans ?? []).join(", ")}</Field>}
          {model.payment_terms && <Field label={t("paymentTerms")}>{model.payment_terms}</Field>}
        </dl>
      )}
    </div>
  );
}
