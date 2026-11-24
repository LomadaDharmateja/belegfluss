"""Run the official KoSIT step-1 XSLT (vendored in ./xslt) with Saxon.

UBL or CII in, one intermediate 'xr' model out (ADR-0014).
"""

from functools import cache
from pathlib import Path

from saxonche import PySaxonApiError, PySaxonProcessor, PyXsltExecutable

from belegfluss.reading.classify import ReadingError, Syntax

XSLT_DIR = Path(__file__).parent / "xslt"
STYLESHEETS = {
    Syntax.UBL_INVOICE: "ubl-invoice-xr.xsl",
    Syntax.UBL_CREDIT_NOTE: "ubl-creditnote-xr.xsl",
    Syntax.CII: "cii-xr.xsl",
}


class _Transformer:
    """Holds one Saxon processor and the compiled stylesheets for the whole process."""

    def __init__(self) -> None:
        self._processor = PySaxonProcessor(license=False)
        xslt = self._processor.new_xslt30_processor()
        self._compiled: dict[Syntax, PyXsltExecutable] = {
            syntax: xslt.compile_stylesheet(stylesheet_file=str(XSLT_DIR / name))
            for syntax, name in STYLESHEETS.items()
        }

    def to_xr(self, xml: bytes, syntax: Syntax) -> bytes:
        try:
            node = self._processor.parse_xml(xml_text=xml.decode("utf-8"))
            result: str | None = self._compiled[syntax].transform_to_string(xdm_node=node)
        except (PySaxonApiError, UnicodeDecodeError) as exc:
            raise ReadingError("BF-XML-UNREADABLE") from exc
        if not result:
            raise ReadingError("BF-XML-UNREADABLE")
        return result.encode("utf-8")


@cache
def _transformer() -> _Transformer:
    return _Transformer()


def to_xr(xml: bytes, syntax: Syntax) -> bytes:
    """`xml` must already have passed `classify.parse_untrusted_xml`."""
    return _transformer().to_xr(xml, syntax)
