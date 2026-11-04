"""Point-in-time views: what the reviewed public record contained on a given date.

A later document must not leak into an account of an earlier date. Each document's availability is
estimated from what the record knows about it: a date from a listing page, the server's Last-Modified
header, or, failing both, the date the document gives itself, which is only a lower bound.
"""

from dataclasses import replace
from datetime import date

from brdo.models import Document
from brdo.store import Dataset
from brdo.vocab import DocumentDateKind


def available_from(document: Document) -> tuple[date | None, str]:
    """The date from which this exact file is taken to have been public, and how that is known."""
    published = sorted((d for d in document.dates if d.kind is DocumentDateKind.PUBLISHED), key=lambda d: d.value)
    if published:
        return published[0].value, str(published[0].basis)
    own = sorted(
        (d for d in document.dates if d.kind in (DocumentDateKind.DATED, DocumentDateKind.SIGNED)),
        key=lambda d: d.value,
    )
    if own:
        return own[-1].value, "not before its own date"
    return None, "unknown"


def as_of(dataset: Dataset, day: date) -> Dataset:
    """The dataset restricted to records whose documents were available by ``day``.

    Documents of unknown availability are left out. Discrepancies are kept only if all their evidence was available.
    """
    kept = {
        document_id
        for document_id, document in dataset.documents.items()
        if (available := available_from(document)[0]) is not None and available <= day
    }
    return replace(
        dataset,
        documents={k: v for k, v in dataset.documents.items() if k in kept},
        provisions={k: v for k, v in dataset.provisions.items() if v.document in kept},
        breach_reports={k: v for k, v in dataset.breach_reports.items() if v.document in kept},
        breach_notices={k: v for k, v in dataset.breach_notices.items() if v.document in kept},
        compliance_statements={k: v for k, v in dataset.compliance_statements.items() if v.document in kept},
        monitoring_censuses={k: v for k, v in dataset.monitoring_censuses.items() if v.document in kept},
        discrepancies={k: v for k, v in dataset.discrepancies.items() if all(e.document in kept for e in v.evidence)},
    )
