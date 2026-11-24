"""The official validator (real container): accepted, rejected with rule codes, not processable."""

import re
from pathlib import Path

import pytest

from belegfluss.settings import Settings
from belegfluss.validation import Outcome, ValidatorClient, ValidatorUnavailableError
from tests.conftest import REPO_ROOT
from tests.test_reading_suite import FILES

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def validator(validator_url: str) -> ValidatorClient:
    return ValidatorClient(validator_url)


def test_all_official_files_are_acceptable(validator: ValidatorClient) -> None:
    if not FILES:
        pytest.skip("Test suite not downloaded: run python scripts/fetch_test_data.py")
    not_accepted = [
        p.name for p in FILES if validator.validate(p.read_bytes()).outcome != Outcome.ACCEPTED
    ]
    assert not_accepted == []


def test_result_names_engine_and_scenario(validator: ValidatorClient) -> None:
    result = validator.validate((FIXTURES / "invoice_cii.xml").read_bytes())
    assert result.engine == "KoSIT Validator 1.6.3"
    assert result.scenario is not None


def test_our_cii_fixture_is_acceptable(validator: ValidatorClient) -> None:
    result = validator.validate((FIXTURES / "invoice_cii.xml").read_bytes())
    errors = [m for m in result.messages if m.severity == "error"]
    assert result.outcome is Outcome.ACCEPTED, errors


def test_wrong_gross_total_is_rejected_with_br_co_15(validator: ValidatorClient) -> None:
    broken = (
        (FIXTURES / "invoice_cii.xml")
        .read_bytes()
        .replace(b"<ram:GrandTotalAmount>447.40<", b"<ram:GrandTotalAmount>500.00<")
    )
    result = validator.validate(broken)
    assert result.outcome is Outcome.REJECTED
    codes = {m.code for m in result.messages if m.severity == "error"}
    assert "BR-CO-15" in codes
    message = next(m for m in result.messages if m.code == "BR-CO-15")
    assert "BT-112" in message.text


def test_garbage_is_not_processable(validator: ValidatorClient) -> None:
    assert validator.validate(b"this is not xml").outcome is Outcome.NOT_PROCESSABLE


def test_unreachable_validator_is_transient() -> None:
    with pytest.raises(ValidatorUnavailableError):
        ValidatorClient("http://127.0.0.1:9", timeout_seconds=2).validate(b"<x/>")


def test_configured_version_matches_the_validator_image() -> None:
    dockerfile = (REPO_ROOT / "services/validator/Dockerfile").read_text(encoding="utf-8")
    config = re.search(r"ARG CONFIG_VERSION=(\S+)", dockerfile)
    assert config is not None
    assert Settings().validator_config.endswith(config.group(1))


# Regression: a ZUGFeRD MINIMUM invoice matches no scenario of the XRechnung configuration. The
# validator answers 406 with <rep:noScenarioMatched>; that means "not checked", not "rejected".
def test_invoice_without_matching_scenario_is_not_checked(validator: ValidatorClient) -> None:
    minimum = (
        (FIXTURES / "invoice_cii.xml")
        .read_bytes()
        .replace(
            b"<ram:ID>urn:cen.eu:en16931:2017</ram:ID>",
            b"<ram:ID>urn:factur-x.eu:1p0:minimum</ram:ID>",
        )
    )
    result = validator.validate(minimum)
    assert result.outcome is Outcome.NO_SCENARIO
    assert result.messages == []
