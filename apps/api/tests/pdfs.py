"""Small test PDFs: a hand-written text layer, and ZUGFeRD/Factur-X PDFs via factur-x."""

import io

import facturx
from pypdf import PdfReader, PdfWriter


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_pdf(lines: list[str]) -> bytes:
    """A one-page PDF with a real text layer (Helvetica, WinAnsi), no external tools."""
    content = (
        "BT /F1 11 Tf 14 TL 50 790 Td " + " ".join(f"({_escape(line)}) '" for line in lines) + " ET"
    )
    stream = content.encode("cp1252")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.7\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)


def zugferd_pdf(xml: bytes, lines: list[str], level: str = "en16931") -> bytes:
    """Embed `xml` as factur-x.xml into a text PDF (PDF/A-3 metadata added by factur-x)."""
    result: bytes = facturx.generate_from_binary(
        text_pdf(lines), xml, flavor="factur-x", level=level, check_xsd=False
    )
    return result


def encrypted_pdf(pdf: bytes, user_password: str) -> bytes:
    """Encrypt a PDF. With an empty user password it opens without asking (only permissions
    are set), as many real-world invoices and receipts do."""
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    writer.encrypt(user_password=user_password, owner_password="owner-secret", algorithm="AES-128")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
