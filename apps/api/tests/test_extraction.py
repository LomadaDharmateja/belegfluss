"""AI extraction without a network: preparation, schema, parsing, verification, request, errors."""

import io
from datetime import date
from decimal import Decimal
from typing import Any

import httpx2
import openai
import pytest
from openai.lib._pydantic import to_strict_json_schema
from PIL import Image
from pypdf import PdfReader, PdfWriter

from belegfluss.extraction import ExtractionFailedError, ExtractorUnavailableError, azure_openai
from belegfluss.extraction.azure_openai import (
    MAX_TEXT_CHARS,
    AzureOpenAIExtractor,
    prompt_fingerprint,
)
from belegfluss.extraction.prepare import Prepared, prepare_pdf, prepare_photo
from belegfluss.extraction.schema import (
    ExtractedInvoice,
    parse_amount,
    parse_date,
    to_invoice_model,
)
from belegfluss.extraction.verify import check_formats, check_presence, iban_is_valid
from belegfluss.reading import ReadingError
from tests.ai_answers import good_answer
from tests.pdfs import text_pdf

# --- parsing and mapping ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1234.56", Decimal("1234.56")),
        ("1.234,56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
        ("12,50 €", Decimal("12.50")),
        ("-3,00", Decimal("-3.00")),
        ("abc", None),
        (None, None),
    ],
)
def test_amounts_are_parsed_exactly(text: str | None, expected: Decimal | None) -> None:
    assert parse_amount(text) == expected


def test_dates_accept_iso_and_german_format_only() -> None:
    assert parse_date("2026-11-18") == date(2026, 11, 18)
    assert parse_date("18.11.2026") == date(2026, 11, 18)
    assert parse_date("31.02.2026") is None
    assert parse_date("Nov 18") is None


def test_answer_maps_to_the_invoice_model() -> None:
    model = to_invoice_model(good_answer())
    assert model.number == "RE-2026-1107"
    assert model.totals.gross == Decimal("447.40")
    assert model.ibans == ["DE02100100100006820101"]
    assert [(v.category, v.rate) for v in model.vat_breakdown] == [("S", 19), ("S", 7)]
    assert model.lines[1].name == "Fachbuch „Wärmepumpen“"


def test_schema_follows_the_strict_structured_output_rules() -> None:
    schema = to_strict_json_schema(ExtractedInvoice)
    forbidden = {
        "pattern",
        "format",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "minItems",
        "maxItems",
    }
    properties = 0

    def walk(node: Any, depth: int) -> int:
        nonlocal properties
        deepest = depth
        if isinstance(node, dict):
            assert not forbidden & node.keys(), node
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
                properties += len(node["properties"])
            for value in node.values():
                deepest = max(
                    deepest,
                    walk(
                        value,
                        depth
                        + (1 if isinstance(value, dict) and value.get("type") == "object" else 0),
                    ),
                )
        elif isinstance(node, list):
            for value in node:
                deepest = max(deepest, walk(value, depth))
        return deepest

    depth = walk(schema, 1)
    assert properties <= 100
    assert depth <= 5


# --- verification ----------------------------------------------------------------------------


def test_iban_checksum() -> None:
    assert iban_is_valid("DE02100100100006820101")
    assert iban_is_valid("DE02 1203 0000 0000 2020 51")
    assert not iban_is_valid("DE02100100100006820102")  # one digit misread
    assert not iban_is_valid("not an iban")


def test_format_checks() -> None:
    model = to_invoice_model(
        good_answer().model_copy(
            update={
                "iban": "DE02100100100006820102",
                "issue_date": "2031-01-01",
                "due_date": "2026-01-01",
            }
        )
    )
    model.seller.vat_id = "DE12345"
    codes = [(f.code, f.params) for f in check_formats(model, date(2026, 11, 24))]
    assert ("BF-AI-INVALID-IBAN", {"value": "DE02100100100006820102"}) in codes
    assert ("BF-AI-INVALID-VAT-ID", {"value": "DE12345"}) in codes
    assert ("BF-AI-IMPLAUSIBLE-DATE", {"field": "issue_date"}) in codes
    assert ("BF-AI-IMPLAUSIBLE-DATE", {"field": "due_date"}) in codes


def test_presence_check_compares_with_the_text_layer() -> None:
    model = to_invoice_model(good_answer())
    text = (
        "Rechnung RE-2026-1107\nUSt-IdNr. DE 987 654 321\n"
        "IBAN DE02 1001 0010 0006 8201 01\nSumme 447,40 €"
    )
    assert check_presence(model, text) == []
    model.number = "RE-2026-1108"
    assert [f.params for f in check_presence(model, text)] == [{"field": "number"}]
    assert check_presence(model, "  ") == []  # photos: nothing to compare


# --- preparation -----------------------------------------------------------------------------


def test_pdf_pages_are_capped_and_rendered() -> None:
    writer = PdfWriter()
    for page in range(5):
        writer.add_page(PdfReader(io.BytesIO(text_pdf([f"Seite {page + 1}"]))).pages[0])
    pdf = io.BytesIO()
    writer.write(pdf)

    prepared = prepare_pdf(pdf.getvalue(), max_pages=3)
    assert prepared.pages == 5
    assert len(prepared.images) == 3
    media_type, png = prepared.images[0]
    assert media_type == "image/png" and png.startswith(b"\x89PNG")
    assert max(Image.open(io.BytesIO(png)).size) <= 1600
    assert "Seite 1" in prepared.text and "Seite 4" not in prepared.text


def test_photos_are_turned_upright_shrunk_and_stripped_of_metadata() -> None:
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90°
    exif[0x8825] = {1: "N", 2: (47.0, 51.0, 0.0)}  # GPS info
    original = io.BytesIO()
    Image.new("RGB", (3000, 1000), "white").save(original, format="JPEG", exif=exif)

    prepared = prepare_photo(original.getvalue())
    media_type, jpeg = prepared.images[0]
    result = Image.open(io.BytesIO(jpeg))
    assert media_type == "image/jpeg"
    assert result.size[1] > result.size[0]  # upright: portrait now
    assert max(result.size) <= 2048
    assert len(result.getexif()) == 0
    assert prepared.text == ""


def test_broken_image_is_reported() -> None:
    with pytest.raises(ReadingError) as caught:
        prepare_photo(b"\x89PNG\r\n\x1a\nnot really")
    assert caught.value.code == "BF-IMAGE-UNREADABLE"


# --- the Azure OpenAI request and its errors (no network) ------------------------------------


class _Responses:
    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class _Client:
    def __init__(self, outcome: Any) -> None:
        self.responses = _Responses(outcome)


class _Usage:
    input_tokens = 2100
    output_tokens = 900


class _Response:
    def __init__(self, parsed: Any) -> None:
        self.output_parsed = parsed
        self.usage = _Usage()
        self.model = "gpt-5.4-mini-2026-03-17"


PREPARED = Prepared(
    images=[("image/png", b"\x89PNG...")], text="x" * (MAX_TEXT_CHARS + 500), pages=1
)


def test_request_is_untrusted_data_without_tools_and_not_stored() -> None:
    client = _Client(_Response(good_answer()))
    extraction = AzureOpenAIExtractor(
        "https://x.openai.azure.com", "gpt-5.4-mini", client=client
    ).extract(PREPARED)
    sent = client.responses.kwargs
    assert sent["model"] == "gpt-5.4-mini"
    assert sent["store"] is False
    assert "tools" not in sent
    assert "untrusted" in sent["instructions"]
    assert sent["text_format"] is ExtractedInvoice
    content = sent["input"][0]["content"]
    assert len(content[0]["text"]) < MAX_TEXT_CHARS + 100  # text layer truncated
    assert content[1]["image_url"].startswith("data:image/png;base64,")
    assert (extraction.input_tokens, extraction.output_tokens) == (2100, 900)


def test_network_and_rate_limit_errors_are_transient() -> None:
    request = httpx2.Request("POST", "https://x.openai.azure.com/openai/v1/responses")
    for error in (
        openai.APIConnectionError(request=request),
        openai.RateLimitError(
            "slow down", response=httpx2.Response(429, request=request), body=None
        ),
    ):
        with pytest.raises(ExtractorUnavailableError):
            AzureOpenAIExtractor("https://x", "d", client=_Client(error)).extract(PREPARED)


def test_bad_request_and_refusal_are_permanent() -> None:
    request = httpx2.Request("POST", "https://x.openai.azure.com/openai/v1/responses")
    bad = openai.BadRequestError("bad", response=httpx2.Response(400, request=request), body=None)
    for outcome in (bad, _Response(None)):
        with pytest.raises(ExtractionFailedError) as caught:
            AzureOpenAIExtractor("https://x", "d", client=_Client(outcome)).extract(PREPARED)
        assert caught.value.code == "BF-AI-FAILED"


def test_prompt_fingerprint_changes_with_anything_that_shapes_the_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = prompt_fingerprint("gpt-5.4-mini", "low", 3)
    assert base == prompt_fingerprint("gpt-5.4-mini", "low", 3)  # stable
    assert base != prompt_fingerprint("gpt-5.4-mini", "medium", 3)
    assert base != prompt_fingerprint("gpt-5.4-mini", "low", 2)
    assert base != prompt_fingerprint("other-model", "low", 3)
    monkeypatch.setattr(azure_openai, "INSTRUCTIONS", azure_openai.INSTRUCTIONS + " Be brief.")
    assert base != prompt_fingerprint("gpt-5.4-mini", "low", 3)
