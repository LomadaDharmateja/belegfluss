import createClient, { type Middleware } from "openapi-fetch";
import type { components, paths } from "./schema";

// Types generated from the API's OpenAPI contract (ADR-0011). Regenerate with `pnpm gen:api`.
export type DocumentOut = components["schemas"]["DocumentOut"];
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
