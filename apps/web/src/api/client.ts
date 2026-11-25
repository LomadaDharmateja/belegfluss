import createClient, { type Middleware } from "openapi-fetch";
import type { components, paths } from "./schema";

// Types generated from the API's OpenAPI contract (ADR-0011). Regenerate with `pnpm gen:api`.
export type DocumentOut = components["schemas"]["DocumentOut"];
export type DocumentDetailOut = components["schemas"]["DocumentDetailOut"];
export type InvoiceOut = components["schemas"]["InvoiceOut"];
export type InvoiceModel = components["schemas"]["InvoiceModel"];
export type FindingOut = components["schemas"]["FindingOut"];
export type InvoiceCorrection = components["schemas"]["InvoiceCorrection"];
export type UploadResult = components["schemas"]["UploadResult"];
export type ErrorBody = components["schemas"]["ErrorBody"];
export type ApiClient = ReturnType<typeof createClient<paths>>;

export function createApiClient(baseUrl: string, getAccessToken: () => Promise<string>): ApiClient {
  const client = createClient<paths>({ baseUrl });
  const auth: Middleware = {
    async onRequest({ request }) {
      request.headers.set("Authorization", `Bearer ${await getAccessToken()}`);
      return request;
    },
  };
  client.use(auth);
  return client;
}

export type UploadOutcome =
  | { kind: "added"; document: DocumentOut }
  | { kind: "duplicate"; document: DocumentOut }
  | { kind: "error"; code: string };

export async function uploadDocument(
  client: ApiClient,
  orgId: string,
  file: File,
): Promise<UploadOutcome> {
  try {
    const { data, error } = await client.POST("/orgs/{org_id}/documents", {
      params: { path: { org_id: orgId } },
      // The contract types a binary part as string; the serializer sends the real File.
      body: { file: file as unknown as string },
      bodySerializer: () => {
        const form = new FormData();
        form.append("file", file);
        return form;
      },
    });
    if (data) {
      return data.duplicate
        ? { kind: "duplicate", document: data.document }
        : { kind: "added", document: data.document };
    }
    return { kind: "error", code: (error as ErrorBody | undefined)?.code ?? "generic" };
  } catch {
    return { kind: "error", code: "network" };
  }
}

/** Result of a change to a document: the new detail, or a stable error code to translate. */
export type DetailOutcome = { ok: true; detail: DocumentDetailOut } | { ok: false; code: string };

function errorCode(error: unknown): string {
  const code = (error as ErrorBody | undefined)?.code;
  return typeof code === "string" ? code : "generic";
}

export async function correctInvoice(
  client: ApiClient,
  orgId: string,
  documentId: string,
  correction: InvoiceCorrection,
): Promise<DetailOutcome> {
  try {
    const { data, error } = await client.PATCH("/orgs/{org_id}/documents/{document_id}/invoice", {
      params: { path: { org_id: orgId, document_id: documentId } },
      body: correction,
    });
    return data ? { ok: true, detail: data } : { ok: false, code: errorCode(error) };
  } catch {
    return { ok: false, code: "network" };
  }
}

export async function approveDocument(
  client: ApiClient,
  orgId: string,
  documentId: string,
  acknowledgeErrors: boolean,
): Promise<DetailOutcome> {
  try {
    const { data, error } = await client.POST("/orgs/{org_id}/documents/{document_id}/approve", {
      params: { path: { org_id: orgId, document_id: documentId } },
      body: { acknowledge_errors: acknowledgeErrors },
    });
    return data ? { ok: true, detail: data } : { ok: false, code: errorCode(error) };
  } catch {
    return { ok: false, code: "network" };
  }
}

export async function reopenDocument(
  client: ApiClient,
  orgId: string,
  documentId: string,
): Promise<DetailOutcome> {
  try {
    const { data, error } = await client.POST("/orgs/{org_id}/documents/{document_id}/reopen", {
      params: { path: { org_id: orgId, document_id: documentId } },
    });
    return data ? { ok: true, detail: data } : { ok: false, code: errorCode(error) };
  } catch {
    return { ok: false, code: "network" };
  }
}

export async function downloadExport(
  client: ApiClient,
  orgId: string,
  period: { from?: string; to?: string },
  lang: "de" | "en",
): Promise<{ ok: true; zip: Blob } | { ok: false; code: string }> {
  try {
    const { data, error } = await client.GET("/orgs/{org_id}/export", {
      params: {
        path: { org_id: orgId },
        query: { from: period.from || undefined, to: period.to || undefined, lang },
      },
      parseAs: "blob",
    });
    return data ? { ok: true, zip: data as Blob } : { ok: false, code: errorCode(error) };
  } catch {
    return { ok: false, code: "network" };
  }
}
