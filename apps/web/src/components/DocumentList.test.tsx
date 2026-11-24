import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DocumentOut } from "@/api/client";
import { renderWithIntl } from "@/test/renderWithIntl";
import { DocumentList } from "./DocumentList";
import { isPending } from "./Inbox";

const received: DocumentOut = {
  id: "7f0c9a4e-0000-0000-0000-000000000001",
  org_id: "7f0c9a4e-0000-0000-0000-0000000000aa",
  original_filename: "Rechnung März.xml",
  media_type: "application/xml",
  size_bytes: 1536,
  sha256: "a".repeat(64),
  source: "upload",
  status: "received",
  created_at: "2026-11-23T10:15:00Z",
  finding_counts: { error: 0, warning: 0, info: 0 },
};

const checked: DocumentOut = {
  ...received,
  id: "7f0c9a4e-0000-0000-0000-000000000002",
  status: "needs_review",
  summary: {
    number: "RE-2026-1107",
    issue_date: "2026-11-18",
    seller_name: "Haustechnik Schäfer GmbH",
    currency: "EUR",
    gross_total: "1447.40",
  },
  finding_counts: { error: 2, warning: 1, info: 3 },
};

describe("DocumentList", () => {
  it("shows an empty state", () => {
    renderWithIntl(<DocumentList documents={[]} />, "en");
    expect(screen.getByText("No documents yet. Add your first invoice above.")).toBeInTheDocument();
  });

  it("shows what was read, in German formats", () => {
    renderWithIntl(<DocumentList documents={[checked]} />, "de");
    expect(screen.getByRole("link", { name: "Rechnung März.xml" })).toHaveAttribute(
      "href",
      `/documents/${checked.id}`,
    );
    expect(screen.getByText("Haustechnik Schäfer GmbH")).toBeInTheDocument();
    expect(screen.getByText("RE-2026-1107")).toBeInTheDocument();
    expect(screen.getByText("18.11.2026")).toBeInTheDocument();
    expect(screen.getByText(/1\.447,40\s€/)).toBeInTheDocument();
    expect(screen.getByText("Bitte prüfen")).toBeInTheDocument();
    expect(screen.getByText("2 Fehler")).toBeInTheDocument();
    expect(screen.getByText("1 Hinweis")).toBeInTheDocument();
  });

  it("shows a document that was not read yet, in English", () => {
    renderWithIntl(<DocumentList documents={[received]} />, "en");
    expect(screen.getByText("Received")).toBeInTheDocument();
    expect(screen.getByText("XML")).toBeInTheDocument();
    expect(screen.getAllByText("–").length).toBeGreaterThanOrEqual(4);
  });
});

describe("isPending (inbox polling)", () => {
  it("polls only while a document waits or is being checked", () => {
    expect(isPending([received])).toBe(true);
    expect(isPending([{ ...received, status: "processing" }])).toBe(true);
    expect(isPending([checked, { ...received, status: "ready" }, { ...received, status: "failed" }])).toBe(false);
  });
});
