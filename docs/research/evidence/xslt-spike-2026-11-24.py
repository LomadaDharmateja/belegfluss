"""Spike: official KoSIT step-1 XSLT (UBL/CII -> xr model) via saxonche, on all suite files.
Usage: spike_xslt.py XSL_DIR SUITE_DIR"""
import sys
import time
from pathlib import Path

from lxml import etree
from saxonche import PySaxonProcessor

xsl_dir, suite_dir = Path(sys.argv[1]), Path(sys.argv[2])
NS = {
    "ubl": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cn": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
}
# Independent XPaths for totals, per syntax (BT-106, 109, 110, 112, 115)
UBL = {
    "BT-106": "//cac:LegalMonetaryTotal/cbc:LineExtensionAmount",
    "BT-109": "//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount",
    "BT-110": "/*/cac:TaxTotal/cbc:TaxAmount[@currencyID=/*/cbc:DocumentCurrencyCode]",
    "BT-112": "//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount",
    "BT-115": "//cac:LegalMonetaryTotal/cbc:PayableAmount",
}
CII = {
    "BT-106": "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:LineTotalAmount",
    "BT-109": "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:TaxBasisTotalAmount",
    "BT-110": "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:TaxTotalAmount[@currencyID=//ram:InvoiceCurrencyCode]",
    "BT-112": "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:GrandTotalAmount",
    "BT-115": "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:DuePayableAmount",
}

def first_text(tree, xpath):
    r = tree.xpath(xpath, namespaces=NS)
    return r[0].text.strip() if r else None

files = sorted(p for p in suite_dir.rglob("*.xml") if "instances" in p.parts)
print(len(files), "suite files")
parser = etree.XMLParser(resolve_entities=False, no_network=True)
with PySaxonProcessor(license=False) as proc:
    print("saxon", proc.version)
    xslt = proc.new_xslt30_processor()
    compiled = {}
    t0 = time.perf_counter()
    for name in ("ubl-invoice-xr.xsl", "ubl-creditnote-xr.xsl", "cii-xr.xsl"):
        compiled[name] = xslt.compile_stylesheet(stylesheet_file=str(xsl_dir / name))
    print(f"compile 3 stylesheets: {time.perf_counter() - t0:.2f}s")
    ok = mismatch = errors = 0
    timings = []
    kinds = {}
    for f in files:
        src = etree.parse(str(f), parser)
        root = etree.QName(src.getroot()).localname
        if root == "Invoice":
            name, paths = "ubl-invoice-xr.xsl", UBL
        elif root == "CreditNote":
            name, paths = "ubl-creditnote-xr.xsl", UBL
        elif root == "CrossIndustryInvoice":
            name, paths = "cii-xr.xsl", CII
        else:
            print("UNKNOWN root", root, f.name); errors += 1; continue
        kinds[name] = kinds.get(name, 0) + 1
        try:
            t = time.perf_counter()
            out = compiled[name].transform_to_string(xdm_node=proc.parse_xml(xml_file_name=str(f)))
            timings.append(time.perf_counter() - t)
        except Exception as e:  # noqa: BLE001
            print("TRANSFORM ERROR", f.name, e); errors += 1; continue
        xr = etree.fromstring(out.encode("utf-8"), parser)
        for bt, xp in paths.items():
            expected = first_text(src, xp)
            got = xr.xpath(f"//*[@xr:id='{bt}']/text()", namespaces={"xr": "urn:ce.eu:en16931:2017:xoev-de:kosit:standard:xrechnung-1"})
            got = got[0].strip() if got else None
            if expected != got and not (expected is None and got is None):
                mismatch += 1
                print(f"MISMATCH {f.name} {bt}: xml={expected!r} xr={got!r}")
        ok += 1
    print("kinds:", kinds)
    print(f"transformed {ok}, errors {errors}, field mismatches {mismatch}")
    timings.sort()
    print(f"per-file transform: median {timings[len(timings)//2]*1000:.1f} ms, max {timings[-1]*1000:.1f} ms")
    first = files[0]
    print("--- sample xr output head for", first.name)
    print(compiled["ubl-invoice-xr.xsl" if "ubl" in first.name else "cii-xr.xsl"].transform_to_string(xdm_node=proc.parse_xml(xml_file_name=str(first)))[:1500])
