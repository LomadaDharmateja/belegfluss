"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import {
  approveDocument,
  correctInvoice,
  reopenDocument,
  type ApiClient,
  type DetailOutcome,
  type DocumentDetailOut,
  type InvoiceCorrection,
} from "@/api/client";
import { useApiClient } from "@/auth/useApiClient";
import { ApprovalBox } from "./ApprovalBox";
import { FindingsList } from "./FindingsList";
import { InvoiceView } from "./InvoiceView";
import { ReviewForm } from "./ReviewForm";
import { StatusBadge } from "./StatusBadge";

const POLL_MS = 2000;

type State =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; orgId: string; detail: DocumentDetailOut };

/** What the page can do with a document; each returns an error code to show, or null. */
type Actions = {
  correct: (correction: InvoiceCorrection) => Promise<string | null>;
  approve: (acknowledgeErrors: boolean) => Promise<string | null>;
  reopen: () => Promise<string | null>;
};

async function fetchDetail(api: ApiClient, documentId: string): Promise<State> {
  try {
    const me = await api.GET("/me");
    const orgId = me.data?.organizations[0]?.id;
    if (!orgId) return { status: "error" };
    const response = await api.GET("/orgs/{org_id}/documents/{document_id}", {
      params: { path: { org_id: orgId, document_id: documentId } },
    });
    return response.data ? { status: "ready", orgId, detail: response.data } : { status: "error" };
  } catch {
    return { status: "error" };
  }
}

export function DocumentDetail({ documentId }: { documentId: string }) {
  const api = useApiClient();
  const t = useTranslations("detail");
  const [state, setState] = useState<State>({ status: "loading" });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    void fetchDetail(api, documentId).then((next) => {
      if (active) setState(next);
    });
    return () => {
      active = false;
    };
  }, [api, documentId, version]);

  const status = state.status === "ready" ? state.detail.document.status : undefined;
  const pending = status === "received" || status === "processing";
  useEffect(() => {
    if (!pending) return;
    const timer = setTimeout(() => setVersion((v) => v + 1), POLL_MS);
    return () => clearTimeout(timer);
  }, [pending, version]);

  // A successful change returns the new detail, which replaces the shown one.
  const apply = async (call: Promise<DetailOutcome>, orgId: string): Promise<string | null> => {
    const outcome = await call;
    if (!outcome.ok) return outcome.code;
    setState({ status: "ready", orgId, detail: outcome.detail });
    return null;
  };
  const actions = (orgId: string): Actions => ({
    correct: (correction) => apply(correctInvoice(api, orgId, documentId, correction), orgId),
    approve: (acknowledge) => apply(approveDocument(api, orgId, documentId, acknowledge), orgId),
    reopen: () => apply(reopenDocument(api, orgId, documentId), orgId),
  });

  return (
    <section className="space-y-6">
      <Link href="/" className="text-sm text-emerald-800 hover:underline">
        ← {t("back")}
      </Link>
      {state.status === "loading" && <p className="text-slate-500">…</p>}
      {state.status === "error" && (
        <p role="alert" className="rounded-md bg-red-50 p-3 text-red-800">
          {t("loadError")}
        </p>
      )}
      {state.status === "ready" && (
        <Detail detail={state.detail} pending={pending} actions={actions(state.orgId)} />
      )}
    </section>
  );
}

function Detail({
  detail,
  pending,
  actions,
}: {
  detail: DocumentDetailOut;
  pending: boolean;
  actions: Actions;
}) {
  const t = useTranslations("detail");
  const tDocuments = useTranslations("documents");
  const tReview = useTranslations("review");
  const { document, invoice, findings } = detail;
  const reviews = detail.reviews ?? [];
  const editable = invoice?.source === "ai" && document.status !== "approved";
  const failureKey = `failureReasons.${document.failure_reason ?? ""}`;
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="break-all text-2xl font-semibold text-slate-900">{document.original_filename}</h1>
        <StatusBadge status={document.status} />
      </div>

      {pending && <p className="text-slate-600">{t("processing")}</p>}
      {document.status === "failed" && (
        <p role="alert" className="rounded-md bg-red-50 p-3 text-red-800">
          {tDocuments.has(failureKey as never) ? tDocuments(failureKey as never) : tDocuments("statusValues.failed")}
        </p>
      )}

      {invoice?.validation_outcome && (
        <div className="rounded-md border border-slate-200 bg-white p-4 text-sm">
          <h2 className="font-medium text-slate-800">{t("validation")}</h2>
          <p className="mt-1">{t(`outcomeValues.${invoice.validation_outcome}`)}</p>
          {invoice.validator_engine && (
            <p className="mt-1 text-xs text-slate-500">
              {t("checkedBy", { engine: invoice.validator_engine, config: invoice.validator_config ?? "–" })}
            </p>
          )}
        </div>
      )}

      {!pending && (
        <section>
          <h2 className="mb-2 text-lg font-medium text-slate-800">{t("findings")}</h2>
          {findings.length > 0 ? <FindingsList findings={findings} /> : <p className="text-slate-600">{t("noFindings")}</p>}
        </section>
      )}

      {editable && (
        // Keyed by the saved values, so the form starts fresh after every save.
        <ReviewForm
          key={JSON.stringify(invoice.model)}
          model={invoice.model}
          findings={findings}
          onSave={actions.correct}
        />
      )}

      {reviews.length > 0 && (
        <section className="text-sm">
          <h2 className="mb-1 font-medium text-slate-800">{tReview("history")}</h2>
          <ul className="space-y-0.5 text-slate-700">
            {reviews.map((review, index) => (
              <li key={index}>
                {tReview("historyLine", {
                  field: tReview.has(`fields.${review.field}` as never) ? tReview(`fields.${review.field}` as never) : review.field,
                  before: review.before ?? tReview("empty"),
                  after: review.after ?? tReview("empty"),
                })}
              </li>
            ))}
          </ul>
        </section>
      )}

      {!pending && document.status !== "failed" && (
        <ApprovalBox document={document} onApprove={actions.approve} onReopen={actions.reopen} />
      )}

      {invoice ? <InvoiceView invoice={invoice} /> : !pending && <p className="text-slate-600">{t("notRead")}</p>}

      <p className="text-xs text-slate-500">{t("disclaimer")}</p>
    </>
  );
}
