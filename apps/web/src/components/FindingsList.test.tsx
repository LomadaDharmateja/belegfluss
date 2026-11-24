import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { FindingOut } from "@/api/client";
import { renderWithIntl } from "@/test/renderWithIntl";
import { FindingsList } from "./FindingsList";

function finding(overrides: Partial<FindingOut>): FindingOut {
  return {
    id: crypto.randomUUID(),
    origin: "belegfluss",
    code: "BF-SMALL-AMOUNT",
    severity: "info",
    message: null,
    location: null,
    business_terms: [],
    params: {},
    ...overrides,
  };
}

describe("FindingsList", () => {
  it("explains our own code with formatted amounts, in German", () => {
    renderWithIntl(
      <FindingsList
        findings={[
          finding({
            code: "BF-VAT-AMOUNT",
            severity: "error",
            params: { rate: "19", expected: "1064.60", actual: "60.00" },
            business_terms: ["BT-117"],
          }),
        ]}
      />,
      "de",
    );
    expect(screen.getByText("Fehler")).toBeInTheDocument();
    expect(
      screen.getByText("Die Umsatzsteuer für 19 % müsste 1.064,60 betragen, auf der Rechnung steht 60,00."),
    ).toBeInTheDocument();
    expect(screen.getByText("Felder: BT-117")).toBeInTheDocument();
  });

  it("explains a curated official rule and keeps the official text available", () => {
    const official = "[BR-CO-15]-Invoice total amount with VAT (BT-112) = ...";
    renderWithIntl(
      <FindingsList
        findings={[finding({ origin: "kosit", code: "BR-CO-15", severity: "error", message: official })]}
      />,
      "en",
    );
    expect(
      screen.getByText("The total with VAT (BT-112) is not the total without VAT plus the VAT."),
    ).toBeInTheDocument();
    expect(screen.getByText("Official rule text")).toBeInTheDocument();
    expect(screen.getByText(official)).toBeInTheDocument();
  });

  it("falls back to the official text for rules without a curated explanation", () => {
    renderWithIntl(
      <FindingsList
        findings={[finding({ origin: "kosit", code: "PEPPOL-EN16931-R999", severity: "warning", message: "Some rule." })]}
      />,
      "en",
    );
    expect(screen.getByText("Some rule.")).toBeInTheDocument();
    expect(screen.queryByText("Official rule text")).not.toBeInTheDocument();
  });

  it("links a duplicate to the other document", () => {
    renderWithIntl(
      <FindingsList
        findings={[finding({ code: "BF-DUPLICATE", severity: "warning", params: { document_id: "abc-123" } })]}
      />,
      "en",
    );
    expect(screen.getByRole("link", { name: "Open the other document" })).toHaveAttribute(
      "href",
      "/documents/abc-123",
    );
  });

  it("shows invoice text as text, never as HTML", () => {
    renderWithIntl(
      <FindingsList
        findings={[finding({ code: "BF-PDF-XML-MISMATCH-NUMBER", severity: "warning", params: { number: "<img src=x onerror=alert(1)>" } })]}
      />,
      "en",
    );
    expect(document.querySelector("img")).toBeNull();
    expect(screen.getByText(/<img src=x onerror=alert\(1\)>/)).toBeInTheDocument();
  });
});
