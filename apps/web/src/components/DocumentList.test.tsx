import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DocumentOut } from "@/api/client";
import { renderWithIntl } from "@/test/renderWithIntl";
import { DocumentList } from "./DocumentList";

const doc: DocumentOut = {
  id: "7f0c9a4e-0000-0000-0000-000000000001",
  org_id: "7f0c9a4e-0000-0000-0000-0000000000aa",
  original_filename: "Rechnung März.xml",
  media_type: "application/xml",
  size_bytes: 1536,
  sha256: "a".repeat(64),
  source: "upload",
  status: "received",
  created_at: "2026-11-23T10:15:00Z",
};

describe("DocumentList", () => {
  it("shows an empty state", () => {
    renderWithIntl(<DocumentList documents={[]} />, "en");
    expect(screen.getByText("No documents yet. Add your first invoice above.")).toBeInTheDocument();
  });

  it("renders a row in German with German number and status formatting", () => {
    renderWithIntl(<DocumentList documents={[doc]} />, "de");
    expect(screen.getByText("Rechnung März.xml")).toBeInTheDocument();
    expect(screen.getByText("Eingegangen")).toBeInTheDocument();
    expect(screen.getByText(/1,5\s?kB/)).toBeInTheDocument(); // German decimal comma
    expect(screen.getByRole("columnheader", { name: "Größe" })).toBeInTheDocument();
  });

  it("renders the same row in English", () => {
    renderWithIntl(<DocumentList documents={[doc]} />, "en");
    expect(screen.getByText("Received")).toBeInTheDocument();
    expect(screen.getByText(/1\.5\s?kB/)).toBeInTheDocument();
    expect(screen.getByText("XML")).toBeInTheDocument();
  });
});
