"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { downloadExport, uploadDocument, type ApiClient, type DocumentOut } from "@/api/client";
import { useApiClient } from "@/auth/useApiClient";
import { DocumentList } from "./DocumentList";
import { ExportBox } from "./ExportBox";
import { UploadDropzone } from "./UploadDropzone";

// Same limit as the API default (BELEGFLUSS_MAX_UPLOAD_BYTES); the API enforces it in any case.
const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
// While documents are being processed, the list refreshes itself (polling, ARCHITECTURE §10.9).
const POLL_MS = 2000;

export function isPending(documents: DocumentOut[]): boolean {
  return documents.some((d) => d.status === "received" || d.status === "processing");
}

type State =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; orgId: string; documents: DocumentOut[] };

async function fetchInbox(api: ApiClient): Promise<State> {
  try {
    const me = await api.GET("/me");
    const orgId = me.data?.organizations[0]?.id;
    if (!orgId) return { status: "error" };
    const docs = await api.GET("/orgs/{org_id}/documents", {
      params: { path: { org_id: orgId } },
    });
    return docs.data ? { status: "ready", orgId, documents: docs.data } : { status: "error" };
  } catch {
    return { status: "error" };
  }
}

export function Inbox() {
  const api = useApiClient();
  const t = useTranslations();
  const locale = useLocale() === "en" ? "en" : "de";
  const [state, setState] = useState<State>({ status: "loading" });
  const [version, setVersion] = useState(0); // bumped after uploads to reload the list

  useEffect(() => {
    let active = true;
    void fetchInbox(api).then((next) => {
      if (active) setState(next);
    });
    return () => {
      active = false;
    };
  }, [api, version]);

  const pending = state.status === "ready" && isPending(state.documents);
  useEffect(() => {
    if (!pending) return;
    const timer = setTimeout(() => setVersion((v) => v + 1), POLL_MS);
    return () => clearTimeout(timer);
  }, [pending, version]);

  return (
    <section className="space-y-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">{t("inbox.title")}</h1>
        {state.status === "ready" && (
          <span className="text-sm text-slate-500">
            {t("inbox.count", { count: state.documents.length })}
          </span>
        )}
      </div>
      {state.status === "loading" && <p className="text-slate-500">{t("app.loading")}</p>}
      {state.status === "error" && (
        <p role="alert" className="rounded-md bg-red-50 p-3 text-red-800">
          {t("inbox.loadError")}
        </p>
      )}
      {state.status === "ready" && (
        <>
          <div>
            <h2 className="mb-3 text-lg font-medium text-slate-800">{t("upload.title")}</h2>
            <UploadDropzone
              maxBytes={MAX_UPLOAD_BYTES}
              upload={(file) => uploadDocument(api, state.orgId, file)}
              onUploaded={() => setVersion((v) => v + 1)}
            />
          </div>
          <DocumentList documents={state.documents} />
          <ExportBox
            onExport={async (period) => {
              const result = await downloadExport(api, state.orgId, period, locale);
              return result.ok ? { zip: result.zip } : { code: result.code };
            }}
          />
        </>
      )}
    </section>
  );
}
