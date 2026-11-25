import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { FindingOut, InvoiceModel } from "@/api/client";
import { renderWithIntl } from "@/test/renderWithIntl";
import { changedFields, initialValues, ReviewForm, uncertainFields } from "./ReviewForm";

const model: InvoiceModel = {
  number: "RE-2O26-11O7",
  issue_date: "2026-11-18",
  currency: "EUR",
  seller: { name: "Haustechnik Schäfer GmbH", vat_id: "DE987654321" },
  ibans: ["DE02100100100006820101"],
  totals: { net: "380.00", vat: "67.40", gross: "447.40", due: "447.40" },
};

function finding(code: string, params: Record<string, string> = {}): FindingOut {
  return { id: crypto.randomUUID(), origin: "belegfluss", code, severity: "warning", message: null, location: null, business_terms: [], params };
}

describe("changedFields", () => {
  it("sends only changed fields, with a decimal point and null for cleared fields", () => {
    const before = initialValues(model);
    const after = { ...before, number: "RE-2026-1107", gross: "447,40", due: "448,00", iban: "" };
    expect(changedFields(before, after)).toEqual({ number: "RE-2026-1107", due: "448.00", iban: null });
  });
});

describe("uncertainFields", () => {
  it("maps findings to the fields the person should look at", () => {
    const fields = uncertainFields([
      finding("BF-AI-NOT-IN-DOCUMENT", { field: "number" }),
      finding("BF-AI-INVALID-IBAN", { value: "x" }),
      finding("BF-AI-IMPLAUSIBLE-DATE", { field: "due_date" }),
    ]);
    expect([...fields].sort()).toEqual(["due_date", "iban", "number"]);
  });
});

describe("ReviewForm", () => {
  it("highlights uncertain fields and saves only the correction", async () => {
    const onSave = vi.fn().mockResolvedValue(null);
    renderWithIntl(
      <ReviewForm model={model} findings={[finding("BF-AI-NOT-IN-DOCUMENT", { field: "number" })]} onSave={onSave} />,
      "de",
    );
    const number = screen.getByLabelText("Rechnungsnummer");
    expect(number).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Lieferant")).not.toHaveAttribute("aria-invalid");

    await userEvent.clear(number);
    await userEvent.type(number, "RE-2026-1107");
    await userEvent.click(screen.getByRole("button", { name: "Korrekturen speichern" }));

    expect(onSave).toHaveBeenCalledWith({ number: "RE-2026-1107" });
    expect(await screen.findByText("Korrekturen gespeichert.")).toBeInTheDocument();
  });

  it("says when nothing changed and shows server errors translated", async () => {
    const onSave = vi.fn().mockResolvedValue("document.approved");
    renderWithIntl(<ReviewForm model={model} findings={[]} onSave={onSave} />, "en");
    await userEvent.click(screen.getByRole("button", { name: "Save corrections" }));
    expect(screen.getByText("Nothing was changed.")).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText("Currency"), "X");
    await userEvent.click(screen.getByRole("button", { name: "Save corrections" }));
    expect(await screen.findByText("This document is approved. Reopen it to make changes.")).toBeInTheDocument();
  });
});
