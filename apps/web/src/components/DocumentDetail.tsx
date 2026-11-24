"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { ApiClient, DocumentDetailOut } from "@/api/client";
import { useApiClient } from "@/auth/useApiClient";
import { FindingsList } from "./FindingsList";
import { InvoiceView } from "./InvoiceView";
import { StatusBadge } from "./StatusBadge";

const POLL_MS = 2000;

type State = { status: "loading" } | { status: "error" } | { status: "ready"; detail: DocumentDetailOut };

async function fetchDetail(api: ApiClient, documentId: string): Promise<State> {
  try {
    const me = await api.GET("/me");
    const orgId = me.data?.organizations[0]?.id;
    if (!orgId) return { status: "error" };
    const response = await api.GET("/orgs/{org_id}/documents/{document_id}", {
      params: { path: { org_id: orgId, document_id: documentId } },
    });
    return response.data ? { status: "ready", detail: response.data } : { status: "error" };
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
      {state.status === "ready" && <Detail detail={state.detail} pending={pending} />}
    </section>
  );
}

function Detail({ detail, pending }: { detail: DocumentDetailOut; pending: boolean }) {
  const t = useTranslations("detail");
  const tDocuments = useTranslations("documents");
  const { document, invoice, findings } = detail;
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

      {invoice ? <InvoiceView invoice={invoice} /> : !pending && <p className="text-slate-600">{t("notRead")}</p>}

      <p className="text-xs text-slate-500">{t("disclaimer")}</p>
    </>
  );
}
