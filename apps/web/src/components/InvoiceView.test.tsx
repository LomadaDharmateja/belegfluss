import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { InvoiceOut } from "@/api/client";
import { renderWithIntl } from "@/test/renderWithIntl";
import { InvoiceView } from "./InvoiceView";

const invoice: InvoiceOut = {
  source: "zugferd",
  syntax: "cii",
  specification_id: "urn:cen.eu:en16931:2017",
  validation_outcome: "accepted",
  validator_engine: "KoSIT Validator 1.6.3",
  validator_config: "xrechnung-3.0.2-2026-08-31",
  validator_scenario: "EN16931 CII",
  pipeline_version: "m2a.1",
  model: {
    number: "RE-2026-1107",
    issue_date: "2026-11-18",
    due_date: "2026-12-02",
    delivery_date: "2026-11-15",
    currency: "EUR",
    seller: {
      name: "Haustechnik Schäfer GmbH",
      vat_id: "DE987654321",
      address: { line1: "Königstraße 7", post_code: "90402", city: "Nürnberg", country_code: "DE" },
    },
    buyer: { name: "Freiberufler Jana Beispiel", address: { city: "Berlin" } },
    ibans: ["DE02100100100006820101"],
    totals: { line_net: "380.00", net: "380.00", vat: "67.40", gross: "447.40", due: "447.40" },
    vat_breakdown: [{ category: "S", rate: "19", taxable_amount: "340.00", tax_amount: "64.60" }],
    lines: [{ id: "1", name: "Fachbuch „Wärmepumpen“", quantity: "1", unit: "H87", unit_price: "40.00", vat_rate: "7", net_amount: "40.00" }],
  },
};

describe("InvoiceView", () => {
  it("shows the read invoice in German formats", () => {
    renderWithIntl(<InvoiceView invoice={invoice} />, "de");
    expect(screen.getByText("ZUGFeRD / Factur-X (PDF mit XML)")).toBeInTheDocument();
    expect(screen.getByText("Haustechnik Schäfer GmbH")).toBeInTheDocument();
    expect(screen.getByText("90402 Nürnberg")).toBeInTheDocument();
    expect(screen.getByText("USt-IdNr.: DE987654321")).toBeInTheDocument();
    expect(screen.getByText("Fachbuch „Wärmepumpen“")).toBeInTheDocument();
    expect(screen.getByText("18.11.2026")).toBeInTheDocument();
    expect(screen.getAllByText(/447,40\s€/)).toHaveLength(2); // total with VAT and amount due
    expect(screen.getByText("S · 19 %")).toBeInTheDocument();
  });

  it("uses English labels", () => {
    renderWithIntl(<InvoiceView invoice={invoice} />, "en");
    expect(screen.getByText("Amount due")).toBeInTheDocument();
    expect(screen.getAllByText(/€447\.40/, { selector: "dd" })).toHaveLength(2);
  });
});
