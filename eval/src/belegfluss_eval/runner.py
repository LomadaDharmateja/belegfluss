"""A live evaluation run: read every document of a split, record the answers (ADR-0018).

Costs money (Azure OpenAI) or free quota (Document Intelligence F0). The run stops once the
estimated spend reaches `max_usd`; it may go over by the cost of one document (about $0.005).
"""

import os
from datetime import UTC, date, datetime
from pathlib import Path

from belegfluss.extraction.azure_openai import prompt_fingerprint
from belegfluss.extraction.prepare import prepare
from belegfluss.settings import Settings

from belegfluss_eval import manifest, recording
from belegfluss_eval.extractors import AzureOpenAI, DocumentIntelligence
from belegfluss_eval.manifest import Split
from belegfluss_eval.paths import DATASET_FILES, MANIFEST, RECORDINGS
from belegfluss_eval.scoring import cost_usd


def _default(name: str) -> str:
    return str(Settings.model_fields[name].default)


def run(
    split: Split,
    extractor: str,
    max_usd: float,
    reasoning_effort: str | None = None,
    image_only: bool = False,
) -> Path:
    data = manifest.load(MANIFEST)
    documents = data.split(split)
    deployment = _default("openai_deployment")
    effort = reasoning_effort or _default("ai_reasoning_effort")
    max_pages = int(_default("ai_max_pages"))

    options: dict[str, str] = {}
    if effort != _default("ai_reasoning_effort"):
        options["reasoning_effort"] = effort
    if image_only:
        options["input"] = "image-only"
    fingerprint = None if extractor == "di" else prompt_fingerprint(deployment, effort, max_pages)
    parts = [date.today().isoformat(), extractor, split, *options.values()]
    run_id = "-".join(parts + ([f"p{fingerprint[:8]}"] if fingerprint else []))

    header = recording.RunHeader(
        run_id=run_id,
        extractor="di" if extractor == "di" else "azure",
        model="",
        deployment=None if extractor == "di" else deployment,
        reasoning_effort=None if extractor == "di" else effort,
        prompt_fingerprint=fingerprint,
        options=options,
        dataset_version=manifest.version(MANIFEST),
        split=split,
        started=datetime.now(UTC),
        today=date.today(),
    )
    if extractor == "di":
        di = DocumentIntelligence(os.environ["BELEGFLUSS_DI_ENDPOINT"])
    else:
        ai = AzureOpenAI(os.environ["BELEGFLUSS_OPENAI_ENDPOINT"], deployment, effort, image_only)

    recordings = []
    spent = 0.0
    for number, doc in enumerate(documents, start=1):
        content = (DATASET_FILES / doc.file).read_bytes()
        prepared = prepare(content, doc.media_type, max_pages)
        if extractor == "di":
            result = di.read(doc.id, content, prepared.text)
        else:
            result = ai.read(doc.id, prepared)
        recordings.append(result)
        spent += cost_usd(header, result, doc.pages)
        status = result.error or "ok"
        progress = f"{number:>4}/{len(documents)} {doc.id:<28} {status:<12}"
        print(f"{progress} {result.seconds:>5.1f}s ${spent:.3f}")
        if spent >= max_usd:
            print(f"cost cap of ${max_usd:.2f} reached: stopped after {number} documents")
            break

    header.model = di.model if extractor == "di" else ai.model
    folder = RECORDINGS / run_id
    recording.write(folder, header, recordings)
    return folder
