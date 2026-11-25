"""Official part of the set: the KoSIT XRechnung test suite, rendered as the official PDF view.

Labels come from the XML with our exact reader (proven on this suite in M2a). The PDF is made with
the official KoSIT visualisation: step-1 XSLT -> `xr-pdf.xsl` (XSL-FO) -> Apache FOP. Language
(de/en) and line layout (normal/tabular) alternate, so there are four official looks.
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from belegfluss.reading import InvoiceModel, classify, read_invoice
from belegfluss.reading.transform import to_xr
from saxonche import PySaxonProcessor

from belegfluss_eval.paths import SUITE, VISUALISATION

FOP_IMAGE = "belegfluss-eval-fop:2.12"
LOOKS = [("de", "normal"), ("en", "tabular"), ("de", "tabular"), ("en", "normal")]


@dataclass(frozen=True)
class Official:
    doc_id: str
    origin: str  # suite file name
    layout: str  # e.g. "kosit-de-normal"
    labels: InvoiceModel
    fo: bytes


def suite_files() -> list[Path]:
    return sorted(SUITE.rglob("*.xml"))


def _labels(xml: bytes) -> tuple[InvoiceModel, bytes]:
    classified = classify(xml, "application/xml", max_pdf_pages=50)
    if classified.syntax is None or classified.xml is None:
        raise RuntimeError("not an XML invoice")
    return read_invoice(classified.xml, classified.syntax), to_xr(classified.xml, classified.syntax)


def prepare_all() -> list[Official]:
    """Labels and XSL-FO for every suite file (Saxon, in process)."""
    processor = PySaxonProcessor(license=False)
    stylesheet = processor.new_xslt30_processor().compile_stylesheet(
        stylesheet_file=str(VISUALISATION / "xsl" / "xr-pdf.xsl")
    )
    stylesheet.set_parameter("foengine", processor.make_string_value("fop"))
    result = []
    for index, path in enumerate(suite_files()):
        labels, xr = _labels(path.read_bytes())
        lang, layout = LOOKS[index % len(LOOKS)]
        stylesheet.set_parameter("lang", processor.make_string_value(lang))
        stylesheet.set_parameter("invoiceline-layout", processor.make_string_value(layout))
        node = processor.parse_xml(xml_text=xr.decode("utf-8"))
        fo = stylesheet.transform_to_string(xdm_node=node)
        if not fo:
            raise RuntimeError(f"no XSL-FO for {path.name}")
        result.append(
            Official(
                doc_id=f"official-{index + 1:03d}",
                origin=path.name,
                layout=f"kosit-{lang}-{layout}",
                labels=labels,
                fo=fo.encode("utf-8"),
            )
        )
    return result


def render(items: list[Official], work: Path) -> dict[str, Path]:
    """XSL-FO -> PDF with Apache FOP in its container. Returns the PDF per document id."""
    work.mkdir(parents=True, exist_ok=True)
    # FOP resolves the font paths in fop.xconf ("fonts/...") next to the input file.
    shutil.copytree(VISUALISATION / "conf" / "fonts", work / "fonts", dirs_exist_ok=True)
    pdfs = {}
    for item in items:
        (work / f"{item.doc_id}.fo").write_bytes(item.fo)
        command = [
            "docker", "run", "--rm",
            "-v", f"{work}:/work",
            "-v", f"{VISUALISATION / 'conf'}:/conf:ro",
            FOP_IMAGE,
            "-c", "/conf/fop.xconf",
            "-cache", "/tmp/fop-fonts.cache",  # noqa: S108 (inside the throwaway container)
            "-fo", f"/work/{item.doc_id}.fo",
            "-pdf", f"/work/{item.doc_id}.pdf",
        ]  # fmt: skip
        subprocess.run(command, check=True, capture_output=True)  # noqa: S603 (fixed command)
        pdfs[item.doc_id] = work / f"{item.doc_id}.pdf"
    return pdfs
