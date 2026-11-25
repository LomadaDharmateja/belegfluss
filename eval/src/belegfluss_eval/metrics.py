"""Field-level comparison with the labels, and the summary numbers of a run.

Strict on purpose: text is compared after removing whitespace and case only, IDs without spaces,
amounts to the cent. A value where the label is empty counts as wrong (it was invented).
"""

import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from statistics import quantiles

from belegfluss.checks import normalise_text
from belegfluss.reading import InvoiceModel

FIELDS = (
    "number",
    "issue_date",
    "due_date",
    "currency",
    "seller_name",
    "seller_vat_id",
    "buyer_name",
    "iban",
    "net",
    "vat",
    "gross",
    "due",
    "vat_breakdown",
    "line_count",
)
# A document counts as correct when everything the accountant export uses is right (header, totals,
# VAT breakdown). Line count is reported on its own: the AI sees at most 3 pages, so long documents
# lose lines by design.
DOCUMENT_FIELDS = tuple(name for name in FIELDS if name != "line_count")
CENT = Decimal("0.01")
ZERO = Decimal("0.00")
_SPACES = re.compile(r"\s+")


def _text(value: str | None) -> str | None:
    if not value:
        return None
    return normalise_text(value) or None


def _id(value: str | None) -> str | None:
    if not value:
        return None
    return _SPACES.sub("", value).upper() or None


def _money(value: Decimal | None) -> Decimal | None:
    return None if value is None else value.quantize(CENT)


def field_values(model: InvoiceModel) -> dict[str, object]:
    """The compared fields, normalised."""
    return {
        "number": _id(model.number),
        "issue_date": model.issue_date,
        "due_date": model.due_date,
        "currency": _id(model.currency),
        "seller_name": _text(model.seller.name),
        "seller_vat_id": _id(model.seller.vat_id),
        "buyer_name": _text(model.buyer.name),
        "iban": _id(model.ibans[0]) if model.ibans else None,
        "net": _money(model.totals.net),
        "vat": _money(model.totals.vat) or ZERO,  # "no VAT" may be written as 0.00 or left out
        "gross": _money(model.totals.gross),
        "due": _money(model.totals.due),
        "vat_breakdown": frozenset(
            (_money(v.rate), _money(v.tax_amount))
            for v in model.vat_breakdown
            if (v.rate or v.tax_amount)  # a 0 % entry only says "no VAT" again
        ),
        "line_count": len(model.lines),
    }


def compare(label: InvoiceModel, read: InvoiceModel) -> dict[str, bool]:
    expected, got = field_values(label), field_values(read)
    return {name: expected[name] == got[name] for name in FIELDS}


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95 % Wilson score interval: honest bounds for a rate measured on few documents."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    denominator = 1 + z * z / n
    return (max(0.0, (centre - margin) / denominator), min(1.0, (centre + margin) / denominator))


@dataclass(frozen=True)
class Scored:
    """One document after reading and checking."""

    doc_id: str
    group: str  # e.g. "official/original", "synthetic/photo"
    fields: dict[str, bool]
    flagged: bool  # got at least one warning or error, or was marked as unreadable
    cost_usd: float
    seconds: float

    @property
    def correct(self) -> bool:
        return all(self.fields[name] for name in DOCUMENT_FIELDS)


@dataclass(frozen=True)
class Summary:
    documents: int
    field_accuracy: dict[str, float]
    document_accuracy: float
    document_interval: tuple[float, float]
    catch_rate: float | None  # wrong documents that were flagged; None if none was wrong
    false_alarm_rate: float | None  # correct documents that were flagged; None if none was correct
    cost_per_document_usd: float
    seconds_p50: float
    seconds_p95: float


def _rate(hits: int, total: int) -> float | None:
    return hits / total if total else None


def _percentile(values: Sequence[float], q: int) -> float:
    if len(values) < 2:
        return values[0] if values else 0.0
    return quantiles(values, n=100, method="inclusive")[q - 1]


def summarise(scored: Iterable[Scored]) -> Summary:
    items = list(scored)
    n = len(items)
    correct = [s for s in items if s.correct]
    wrong = [s for s in items if not s.correct]
    seconds = [s.seconds for s in items]
    return Summary(
        documents=n,
        field_accuracy={
            name: (sum(s.fields[name] for s in items) / n if n else 0.0) for name in FIELDS
        },
        document_accuracy=len(correct) / n if n else 0.0,
        document_interval=wilson(len(correct), n),
        catch_rate=_rate(sum(s.flagged for s in wrong), len(wrong)),
        false_alarm_rate=_rate(sum(s.flagged for s in correct), len(correct)),
        cost_per_document_usd=sum(s.cost_usd for s in items) / n if n else 0.0,
        seconds_p50=_percentile(seconds, 50),
        seconds_p95=_percentile(seconds, 95),
    )


def by_group(scored: Iterable[Scored]) -> dict[str, Summary]:
    groups: dict[str, list[Scored]] = {}
    for s in scored:
        groups.setdefault(s.group, []).append(s)
    return {name: summarise(items) for name, items in sorted(groups.items())}
