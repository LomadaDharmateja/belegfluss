import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { DocumentOut } from "@/api/client";
import { renderWithIntl } from "@/test/renderWithIntl";
import { ApprovalBox } from "./ApprovalBox";
import { ExportBox } from "./ExportBox";

const document_: DocumentOut = {
  id: "d1",
  org_id: "o1",
  original_filename: "scan.pdf",
  media_type: "application/pdf",
  size_bytes: 10,
  sha256: "a".repeat(64),
  source: "upload",
  status: "needs_review",
  created_at: "2026-11-24T10:00:00Z",
  finding_counts: { error: 0, warning: 1, info: 1 },
};

describe("ApprovalBox", () => {
  it("approves directly when no errors are open", async () => {
    const onApprove = vi.fn().mockResolvedValue(null);
    renderWithIntl(<ApprovalBox document={document_} onApprove={onApprove} onReopen={vi.fn()} />, "en");
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(onApprove).toHaveBeenCalledWith(false);
  });

  it("needs the acknowledgement while errors are open", async () => {
    const onApprove = vi.fn().mockResolvedValue(null);
    const withErrors = { ...document_, finding_counts: { error: 2, warning: 0, info: 0 } };
    renderWithIntl(<ApprovalBox document={withErrors} onApprove={onApprove} onReopen={vi.fn()} />, "de");
    const button = screen.getByRole("button", { name: "Freigeben" });
    expect(button).toBeDisabled();
    await userEvent.click(screen.getByLabelText("Ich habe die Fehler gesehen und möchte trotzdem freigeben."));
    await userEvent.click(button);
    expect(onApprove).toHaveBeenCalledWith(true);
  });

  it("offers to reopen an approved document", async () => {
    const onReopen = vi.fn().mockResolvedValue(null);
    const approved = { ...document_, status: "approved" as const, approved_at: "2026-11-24T11:00:00Z" };
    renderWithIntl(<ApprovalBox document={approved} onApprove={vi.fn()} onReopen={onReopen} />, "en");
    expect(screen.getByText(/Approved on/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reopen" }));
    expect(onReopen).toHaveBeenCalled();
  });
});

describe("ExportBox", () => {
  it("requests the chosen period and shows a translated error", async () => {
    const onExport = vi.fn().mockResolvedValue({ code: "export.too_large" });
    renderWithIntl(<ExportBox onExport={onExport} />, "en");
    await userEvent.type(screen.getByLabelText("From"), "2026-11-01");
    await userEvent.click(screen.getByRole("button", { name: "Download ZIP" }));
    expect(onExport).toHaveBeenCalledWith({ from: "2026-11-01", to: "" });
    expect(await screen.findByText("Too many documents. Please choose a shorter period.")).toBeInTheDocument();
  });
});
