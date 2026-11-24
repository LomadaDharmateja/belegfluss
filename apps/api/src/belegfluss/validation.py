"""Client for the official KoSIT validator daemon (ADR-0005).

200 = acceptable, 406 = not acceptable, 422 = the validator couldn't process the document.
Anything else (or no connection) means the validator is unavailable: the worker retries later.
"""

from dataclasses import dataclass, field
from enum import StrEnum

import httpx2
from lxml import etree

REP = {"rep": "http://www.xoev.de/de/validator/varl/1"}
SEVERITY = {"error": "error", "warning": "warning", "information": "info"}


class Outcome(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NOT_PROCESSABLE = "not_processable"


@dataclass(frozen=True)
class Message:
    code: str
    severity: str  # error | warning | info
    text: str
    location: str | None


@dataclass(frozen=True)
class ValidationResult:
    outcome: Outcome
    engine: str  # e.g. "KoSIT Validator 1.6.3", from the report
    scenario: str | None  # e.g. "EN16931 XRechnung (UBL Invoice)"
    messages: list[Message] = field(default_factory=list)


class ValidatorUnavailableError(Exception):
    """Transient: retry later."""


def parse_report(report: bytes) -> tuple[str, str | None, list[Message]]:
    root = etree.fromstring(report, etree.XMLParser(resolve_entities=False, no_network=True))
    engine = root.findtext("rep:engine/rep:name", default="KoSIT Validator", namespaces=REP).strip()
    scenario = root.findtext("rep:scenarioMatched/*/{*}name", namespaces=REP)
    messages = [
        Message(
            code=element.get("code") or "UNKNOWN",
            severity=SEVERITY.get(element.get("level", "error"), "error"),
            text=" ".join((element.text or "").split()),
            location=element.get("xpathLocation"),
        )
        for element in root.iterfind(".//rep:message", REP)
    ]
    return engine, scenario.strip() if scenario else None, messages


class ValidatorClient:
    def __init__(self, base_url: str, timeout_seconds: float = 30.0) -> None:
        self._http = httpx2.Client(base_url=base_url, timeout=timeout_seconds)

    def validate(self, xml: bytes) -> ValidationResult:
        try:
            response = self._http.post(
                "/", content=xml, headers={"Content-Type": "application/xml"}
            )
        except httpx2.TransportError as exc:
            raise ValidatorUnavailableError(type(exc).__name__) from exc

        outcomes = {200: Outcome.ACCEPTED, 406: Outcome.REJECTED, 422: Outcome.NOT_PROCESSABLE}
        outcome = outcomes.get(response.status_code)
        if outcome is None:
            raise ValidatorUnavailableError(f"HTTP {response.status_code}")
        try:
            engine, scenario, messages = parse_report(response.content)
        except etree.XMLSyntaxError:
            if outcome is not Outcome.NOT_PROCESSABLE:
                raise ValidatorUnavailableError("unreadable report") from None
            engine, scenario, messages = "KoSIT Validator", None, []
        return ValidationResult(outcome, engine, scenario, messages)

    def close(self) -> None:
        self._http.close()
