"""Point-in-time views: what the reviewed public record contained on a given date.

A later document must not leak into an account of an earlier date. The record holds three different kinds of
evidence about when a file became public, and keeps them apart:

* a lower bound, the latest date the file gives itself (its date, signature, "as on" date, or the date of a letter it
  contains). It cannot have been public before then;
* an estimate, from the publisher's own listing date or, failing that, the server's Last-Modified header for the
  exact file held. Last-Modified dates that version on the server, so an earlier version may have been public sooner,
  and a copied file can carry a misleading date;
* an observation, the day the project retrieved the file from its public address. This is the only date the record
  proves, and it is usually much later than first publication.

``as_of`` builds the view from either the estimate (the default) or the observation, and removes from it every
record, claim, observation and piece of evidence that the chosen dates do not show to have been public by the day.
"""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date

from brdo.models import Document, Evidence, Observation
from brdo.store import Dataset
from brdo.vocab import AvailabilityMode, DocumentDateKind

OWN_DATE_BASIS = "not before its own date"
OBSERVED_BASIS = "observed by the project"


@dataclass(frozen=True)
class Availability:
    """What the record shows about when one exact file became public."""

    not_before: date | None
    """The file cannot have been public before this day, the latest date it gives itself or a letter in it carries."""
    estimate: date | None
    """Best estimate of the day this exact file became public."""
    estimate_basis: str
    observed: date | None
    """The day the file was observed to be public, which is when the project retrieved it."""
    observed_basis: str
    last_modified: date | None = None
    published: date | None = None

    @property
    def estimate_precedes_own_date(self) -> bool:
        """The server or the publisher dates the file before the file's own date, which cannot be right."""
        dates = [d for d in (self.last_modified, self.published) if d is not None]
        return self.not_before is not None and any(d < self.not_before for d in dates)

    @property
    def dated_after_observation(self) -> bool:
        """A date recorded for the file falls after the project retrieved it, which cannot be right."""
        dates = [d for d in (self.last_modified, self.published, self.not_before) if d is not None]
        return self.observed is not None and any(d > self.observed for d in dates)


def _own_dates(document: Document, dataset: Dataset | None) -> list[date]:
    own = [d.value for d in document.dates if d.kind in (DocumentDateKind.DATED, DocumentDateKind.SIGNED)]
    if document.as_of is not None:
        own.append(document.as_of)
    if dataset is not None:
        own += [notice.issued_on for notice in dataset.breach_notices.values() if notice.document == document.id]
    return own


def availability(document: Document, dataset: Dataset | None = None) -> Availability:
    """Bounds and an estimate for when this exact file became public, each with how it is known.

    With ``dataset``, the dates of letters transcribed from the file also bound it from below.
    """
    not_before = max(_own_dates(document, dataset), default=None)
    published = min((d.value for d in document.dates if d.kind is DocumentDateKind.PUBLISHED), default=None)
    last_modified = max((d.value for d in document.dates if d.kind is DocumentDateKind.LAST_MODIFIED), default=None)
    observed = document.retrieved_at.date() if document.retrieved_at else None
    observed_basis = (
        "unknown"
        if observed is None
        else "retrieved manually"
        if document.retrieved_manually
        else "retrieved by pipeline"
    )

    candidates: list[tuple[date, str]] = []
    if published is not None:
        published_basis = next(
            d.basis for d in document.dates if d.kind is DocumentDateKind.PUBLISHED and d.value == published
        )
        candidates.append((published, str(published_basis)))
    if last_modified is not None:
        candidates.append((last_modified, "http_last_modified"))
    if candidates:
        # The later of the publisher's date and the server's: a file listed earlier may since have been replaced,
        # and a file uploaded earlier may only have been listed later. Ties keep the publisher's own date.
        estimate, basis = max(candidates, key=lambda candidate: candidate[0])
        if not_before is not None and estimate < not_before:
            estimate, basis = not_before, OWN_DATE_BASIS
    elif not_before is not None:
        estimate, basis = not_before, OWN_DATE_BASIS
    elif observed is not None:
        estimate, basis = observed, OBSERVED_BASIS
    else:
        estimate, basis = None, "unknown"
    return Availability(
        not_before=not_before,
        estimate=estimate,
        estimate_basis=basis,
        observed=observed,
        observed_basis=observed_basis,
        last_modified=last_modified,
        published=published,
    )


def available_from(document: Document, dataset: Dataset | None = None) -> tuple[date | None, str]:
    """The estimated date from which this exact file was public, and how that is known."""
    found = availability(document, dataset)
    return found.estimate, found.estimate_basis


def _shown_public_by(document: Document, dataset: Dataset, mode: AvailabilityMode) -> date | None:
    found = availability(document, dataset)
    return found.observed if mode is AvailabilityMode.OBSERVED else found.estimate


def as_of(dataset: Dataset, day: date, mode: AvailabilityMode = AvailabilityMode.ESTIMATED) -> Dataset:
    """The dataset as the public record stood on ``day``, judged by the availability dates ``mode`` trusts.

    Every record, claim, name variant, document link and discrepancy is kept only if what supports it was public by
    ``day``, and the evidence lists of those kept are cut to the documents that were. Observations made on pages the
    project may not store count from the day they were made. Documents of unknown availability are left out.

    The search log is kept whole. It records the project's own searches, mostly made later than ``day``, and status
    derivation reads a search that later found a document as evidence that the document existed, never that it was
    public by ``day``.
    """
    kept = {
        document_id
        for document_id, document in dataset.documents.items()
        if (shown := _shown_public_by(document, dataset, mode)) is not None and shown <= day
    }

    def evidence(items: Iterable[Evidence]) -> list[Evidence]:
        return [item for item in items if item.document in kept]

    def observations(items: Iterable[Observation]) -> list[Observation]:
        return [item for item in items if item.observed_on <= day]

    instruments = {}
    for isin, instrument in dataset.instruments.items():
        claims = [
            claim.model_copy(
                update={"evidence": evidence(claim.evidence), "observations": observations(claim.observations)}
            )
            for claim in instrument.claims
            if evidence(claim.evidence) or observations(claim.observations)
        ]
        links = [
            link.model_copy(update={"evidence": evidence(link.evidence)})
            for link in instrument.documents
            if link.document in kept and evidence(link.evidence)
        ]
        instruments[isin] = instrument.model_copy(update={"claims": claims, "documents": links})

    issuers = {}
    for issuer_id, issuer in dataset.issuers.items():
        variants = [
            variant.model_copy(update={"evidence": evidence(variant.evidence)})
            for variant in issuer.name_variants
            if evidence(variant.evidence)
        ]
        issuers[issuer_id] = issuer.model_copy(
            update={"name_variants": variants, "observations": observations(issuer.observations)}
        )

    return replace(
        dataset,
        documents={k: v for k, v in dataset.documents.items() if k in kept},
        issuers=issuers,
        instruments=instruments,
        provisions={k: v for k, v in dataset.provisions.items() if v.document in kept},
        breach_reports={k: v for k, v in dataset.breach_reports.items() if v.document in kept},
        breach_notices={k: v for k, v in dataset.breach_notices.items() if v.document in kept},
        compliance_statements={k: v for k, v in dataset.compliance_statements.items() if v.document in kept},
        monitoring_censuses={k: v for k, v in dataset.monitoring_censuses.items() if v.document in kept},
        regulatory_references={k: v for k, v in dataset.regulatory_references.items() if v.document in kept},
        discrepancies={
            k: v
            for k, v in dataset.discrepancies.items()
            if all(e.document in kept for e in v.evidence) and all(o.observed_on <= day for o in v.observations)
        },
        cutoff=day if dataset.cutoff is None else min(day, dataset.cutoff),
        availability_mode=mode,
        withheld=dataset.withheld | {k: v for k, v in dataset.documents.items() if k not in kept},
    )
