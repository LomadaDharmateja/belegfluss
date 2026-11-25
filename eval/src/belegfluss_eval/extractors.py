"""Live calls for one document: Azure OpenAI (the product) or Document Intelligence (the baseline).

Both sign in keyless (DefaultAzureCredential: `az login` locally, the OIDC identity in GitHub
Actions).
The answer is stored as plain JSON in a `Recording`; turning it into an InvoiceModel happens later
in `scoring`, so recordings can be scored again with newer code.
"""

import io
import time
from typing import Any

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentField
from azure.identity import DefaultAzureCredential
from belegfluss.extraction import ExtractionFailedError, ExtractorUnavailableError
from belegfluss.extraction.azure_openai import AzureOpenAIExtractor
from belegfluss.extraction.prepare import Prepared

from belegfluss_eval.recording import Recording

RETRIES = 3


class AzureOpenAI:
    def __init__(self, endpoint: str, deployment: str, reasoning_effort: str, image_only: bool):
        self.extractor = AzureOpenAIExtractor(endpoint, deployment, reasoning_effort)
        self.image_only = image_only
        self.model = ""

    def read(self, doc_id: str, prepared: Prepared) -> Recording:
        sent = Prepared(prepared.images, "", prepared.pages) if self.image_only else prepared
        for attempt in range(RETRIES):
            try:
                extraction = self.extractor.extract(sent)
            except ExtractorUnavailableError:
                if attempt == RETRIES - 1:
                    return Recording(
                        doc_id=doc_id, answer=None, error="unavailable", text=prepared.text
                    )
                time.sleep(10 * (attempt + 1))
                continue
            except ExtractionFailedError as exc:
                return Recording(doc_id=doc_id, answer=None, error=exc.code, text=prepared.text)
            self.model = extraction.model
            return Recording(
                doc_id=doc_id,
                answer=extraction.invoice.model_dump(),
                text=prepared.text,  # the verification always uses the real text layer
                input_tokens=extraction.input_tokens,
                output_tokens=extraction.output_tokens,
                seconds=extraction.seconds,
            )
        raise AssertionError("unreachable")


def _plain(field: DocumentField | None) -> Any:
    """A Document Intelligence field as plain JSON."""
    if field is None:
        return None
    if field.value_currency is not None:
        return {
            "amount": field.value_currency.amount,
            "currency": field.value_currency.currency_code,
        }
    if field.value_date is not None:
        return field.value_date.isoformat()
    if field.value_array is not None:
        return [_plain(item) for item in field.value_array]
    if field.value_object is not None:
        return {name: _plain(value) for name, value in field.value_object.items()}
    if field.value_number is not None:
        return field.value_number
    return field.value_string if field.value_string is not None else field.content


DI_FIELDS = (
    "InvoiceId", "InvoiceDate", "DueDate", "VendorName", "VendorTaxId", "CustomerName",
    "SubTotal", "TotalTax", "InvoiceTotal", "AmountDue", "PaymentDetails", "TaxDetails",
)  # fmt: skip


class DocumentIntelligence:
    """Model `prebuilt-invoice`, API 2024-11-30. F0: first 2 pages only, 1 request per second."""

    def __init__(self, endpoint: str):
        self.client = DocumentIntelligenceClient(endpoint, DefaultAzureCredential())
        self.model = "prebuilt-invoice (2024-11-30)"

    def read(self, doc_id: str, data: bytes, text: str) -> Recording:
        started = time.monotonic()
        try:
            poller = self.client.begin_analyze_document("prebuilt-invoice", body=io.BytesIO(data))
            result = poller.result()
        except Exception as exc:  # any service error: recorded, the run goes on
            return Recording(doc_id=doc_id, answer=None, error=type(exc).__name__, text=text)
        seconds = time.monotonic() - started
        time.sleep(max(0.0, 1.1 - seconds))  # F0: at most one request per second
        documents = result.documents or []
        fields: dict[str, DocumentField] = {}
        if documents and documents[0].fields:
            fields = documents[0].fields
        answer = {name: _plain(fields.get(name)) for name in DI_FIELDS}
        items = fields.get("Items")
        answer["ItemCount"] = len(items.value_array or []) if items else 0
        return Recording(doc_id=doc_id, answer=answer, text=text, seconds=round(seconds, 2))
