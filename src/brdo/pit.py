"""Point-in-time views: what the reviewed public record established on a given date.

A historical view must not expose anything that the evidence available on its date did not establish. That needs
two things this module keeps explicit.

**When a file was public is uncertain, and the record keeps the kinds of evidence apart.**

* A lower bound. A file cannot have been public before the latest date it gives itself, before a letter it
  contains was dated, or before the latest event it reports. This assumes those dates are right.
* A publisher's own date, such as a listing page's date: the publisher's claim about when it posted the file.
* The server's Last-Modified date, which dates the version of the file the server held. It is not the file's
  first publication: a file can be uploaded before it is linked, replaced, or copied with a misleading date.
* The day the project retrieved the file from its public address. That proves the file was public by then. It is
  usually much later than first publication.

The estimate is the later of the publisher's date and the server's date, never before the lower bound. It is a
conservative estimate of when this exact file was at its address, not a publication date, and it can still be early
when a server's date predates the file's appearance.

**Entities and their attributes need support too.** An ISIN, the issuer it belongs to, an issuer's name and its CIN
or LEI each appear in a view only if a record that prints them was shown public by the view's date (``supports``).

``as_of`` builds the view from the estimates (the public record as reconstructed) or from the project's own
observations (what the project had itself seen). Free-text notes written later are dropped, and so are searches made
after the date. Nothing in a view says what the full record holds beyond it.

A test can show that these rules are applied consistently. It cannot show that the dates the rules use are
historically right: a wrong Last-Modified header gives a consistently wrong view.
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace
from datetime import date

from brdo.models import Document, Evidence, Observation, Provision
from brdo.pdftext import normalize
from brdo.review import reviewed_records
from brdo.store import Dataset
from brdo.vocab import AvailabilityMode, DocumentDateKind

OWN_DATE_BASIS = "not before its own date"
CONFIRMED_BASIS = "observed by the project"


@dataclass(frozen=True)
class Availability:
    """What the record shows about when one exact file was public. Only ``confirmed_by`` is proved by the record."""

    not_before: date | None
    """Lower bound: the file cannot have been public before this day, if the dates it prints are right."""
    not_before_basis: str
    estimate: date | None
    """Conservative estimate of when this exact file was at its address. Not a publication date."""
    estimate_basis: str
    confirmed_by: date | None
    """The project retrieved the file from its public address on this day, so it was public by then."""
    confirmed_basis: str
    last_modified: date | None = None
    published: date | None = None
    """The publisher's own date for the file, such as a listing page's."""

    @property
    def window_days(self) -> int | None:
        """Width of the interval in which the file first became public, when both ends are known."""
        if self.not_before is None or self.confirmed_by is None:
            return None
        return (self.confirmed_by - self.not_before).days

    @property
    def estimate_precedes_own_date(self) -> bool:
        """The server or the publisher dates the file before its lower bound, which cannot both be right."""
        dates = [d for d in (self.last_modified, self.published) if d is not None]
        return self.not_before is not None and any(d < self.not_before for d in dates)

    @property
    def dated_after_observation(self) -> bool:
        """A date recorded for the file falls after the project retrieved it, which cannot be right."""
        dates = [d for d in (self.last_modified, self.published, self.not_before) if d is not None]
        return self.confirmed_by is not None and any(d > self.confirmed_by for d in dates)


def _lower_bounds(document: Document, dataset: Dataset | None) -> list[tuple[date, str]]:
    bounds = [
        (d.value, "its own date") for d in document.dates if d.kind in (DocumentDateKind.DATED, DocumentDateKind.SIGNED)
    ]
    if document.as_of is not None:
        bounds.append((document.as_of, "its own date"))
    if dataset is None:
        return bounds
    bounds += [
        (notice.issued_on, "a letter it contains")
        for notice in dataset.breach_notices.values()
        if notice.document == document.id
    ]
    report = dataset.breach_reports.get(document.id)
    if report is not None:
        for row in report.rows:
            events = [
                row.detected.value if row.detected else None,
                row.actual_breach.value if row.actual_breach else None,
            ]
            events += [intimation.dated for intimation in row.intimations]
            bounds += [(day, "an event it reports") for day in events if day is not None]
    return bounds


def availability(document: Document, dataset: Dataset | None = None) -> Availability:
    """The evidence on when this exact file was public, kept apart, with an estimate and how each is known.

    With ``dataset``, the dates of letters transcribed from the file and of events its rows report also bound it from
    below.
    """
    bounds = _lower_bounds(document, dataset)
    not_before, not_before_basis = max(bounds, default=(None, "unknown"), key=lambda bound: bound[0] or date.min)
    published = min((d.value for d in document.dates if d.kind is DocumentDateKind.PUBLISHED), default=None)
    last_modified = max((d.value for d in document.dates if d.kind is DocumentDateKind.LAST_MODIFIED), default=None)
    confirmed = document.retrieved_at.date() if document.retrieved_at else None
    confirmed_basis = (
        "unknown"
        if confirmed is None
        else "retrieved manually"
        if document.retrieved_manually
        else "retrieved by pipeline"
    )

    candidates: list[tuple[date, str]] = []
    if published is not None:
        basis = next(d.basis for d in document.dates if d.kind is DocumentDateKind.PUBLISHED and d.value == published)
        candidates.append((published, str(basis)))
    if last_modified is not None:
        candidates.append((last_modified, "http_last_modified"))
    if candidates:
        # The later of the two: a file listed earlier may since have been replaced, and a file uploaded earlier may only
        # have been listed later. Ties keep the publisher's date. Neither can establish first publication.
        estimate, estimate_basis = max(candidates, key=lambda candidate: candidate[0])
        if not_before is not None and estimate < not_before:
            estimate, estimate_basis = not_before, f"not before {not_before_basis}"
    elif not_before is not None:
        estimate, estimate_basis = not_before, f"not before {not_before_basis}"
    elif confirmed is not None:
        estimate, estimate_basis = confirmed, CONFIRMED_BASIS
    else:
        estimate, estimate_basis = None, "unknown"
    return Availability(
        not_before=not_before,
        not_before_basis=not_before_basis,
        estimate=estimate,
        estimate_basis=estimate_basis,
        confirmed_by=confirmed,
        confirmed_basis=confirmed_basis,
        last_modified=last_modified,
        published=published,
    )


def available_from(document: Document, dataset: Dataset | None = None) -> tuple[date | None, str]:
    """The estimated date from which this exact file was at its address, and how that is known."""
    found = availability(document, dataset)
    return found.estimate, found.estimate_basis


def shown_public_by(document: Document, dataset: Dataset, mode: AvailabilityMode) -> date | None:
    """The day from which ``mode`` treats this file as public."""
    found = availability(document, dataset)
    return found.confirmed_by if mode is AvailabilityMode.OBSERVED else found.estimate


@dataclass(frozen=True)
class Support:
    """A record that establishes one attribute of an instrument or issuer, through a document or an observation.

    ``attribute`` is ``identity`` for an instrument (the ISIN, and the issuer the dataset assigns it to), or
    ``identity``, ``name``, ``cin`` or ``lei`` for an issuer.
    """

    entity: str
    key: str
    attribute: str
    record: str
    document: str | None = None
    observation: Observation | None = None


_ABBREVIATIONS = ((r"\bltd\b\.?", "limited"), (r"\bpvt\b\.?", "private"), (r"&", " and "), (r"[^a-z0-9 ]", " "))


def name_key(name: str) -> str:
    """A name folded for matching: case, punctuation, and "Ltd"/"Pvt" against "Limited"/"Private"."""
    text = normalize(name)
    for pattern, replacement in _ABBREVIATIONS:
        text = re.sub(pattern, replacement, text)
    return " ".join(text.split())


def _isin_supports(dataset: Dataset) -> Iterator[Support]:
    """Records that print an ISIN of the dataset's instruments. A letter or statement not printing it does not count."""

    def instrument(isin: str, record: str, document: str | None = None, observation: Observation | None = None):
        if isin in dataset.instruments:
            yield Support("instrument", isin, "identity", record, document, observation)

    for isin, held in dataset.instruments.items():
        for claim in held.claims:
            for item in claim.evidence:
                yield from instrument(isin, f"claim {claim.property} by {claim.asserted_by}", item.document)
            for seen in claim.observations:
                yield from instrument(isin, f"claim {claim.property} by {claim.asserted_by}", observation=seen)
        for link in held.documents:
            for item in link.evidence:
                yield from instrument(isin, f"link to {link.document}", item.document)
    for report in dataset.breach_reports.values():
        for row in report.rows:
            for isin in row.isins:
                yield from instrument(isin, f"breach report {report.document} row {row.row}", report.document)
    for notice in dataset.breach_notices.values():
        if notice.isins_printed:
            for isin in notice.isins:
                yield from instrument(isin, f"letter {notice.id}", notice.document)
    for statement in dataset.compliance_statements.values():
        printed = {isin for line in statement.exceptions for isin in line.isins}
        if statement.isins_printed:
            printed |= set(statement.instruments)
        for isin in sorted(printed):
            yield from instrument(isin, f"statement {statement.id}", statement.document)
    for census in dataset.monitoring_censuses.values():
        printed = {entry.isin for entry in census.entries} | set(census.sample) | set(census.report_not_received)
        for isin in sorted(printed):
            yield from instrument(isin, f"census {census.id}", census.document)


def all_observations(dataset: Dataset) -> Iterator[tuple[str, Observation]]:
    for issuer in dataset.issuers.values():
        for seen in issuer.observations:
            yield f"issuer {issuer.id} observation", seen
    for held in dataset.instruments.values():
        for claim in held.claims:
            for seen in claim.observations:
                yield f"instrument {held.isin} claim {claim.property}", seen
    for discrepancy in dataset.discrepancies.values():
        for seen in discrepancy.observations:
            yield f"discrepancy {discrepancy.id}", seen


def supports(dataset: Dataset) -> list[Support]:
    """Every record that establishes an instrument's identity, or an issuer's identity, name, CIN or LEI.

    An instrument is established by a record that prints its ISIN; the record is taken to establish the issuer the
    dataset assigns the ISIN to as well, since every such record in this dataset is a disclosure by or about that
    issuer.
    An issuer's name is established by a record printing it, possibly with additions such as a former name; its CIN or
    LEI only by an anchor or observation that prints the identifier itself.
    """
    found = list(_isin_supports(dataset))
    by_isin: dict[str, list[Support]] = {}
    for support in found:
        by_isin.setdefault(support.key, []).append(support)
    anchors = list(dataset.evidence())
    observations = list(all_observations(dataset))
    for issuer in dataset.issuers.values():
        own = [i for i in dataset.instruments.values() if i.issuer == issuer.id]
        found += [
            Support("issuer", issuer.id, "identity", support.record, support.document, support.observation)
            for held in own
            for support in by_isin.get(held.isin, [])
        ]
        found += [
            Support("issuer", issuer.id, "identity", f"issuer {issuer.id} name variant", item.document)
            for variant in issuer.name_variants
            for item in variant.evidence
        ]
        found += [
            Support("issuer", issuer.id, "identity", f"issuer {issuer.id} observation", observation=seen)
            for seen in issuer.observations
        ]
        base = name_key(issuer.name)
        for report in dataset.breach_reports.values():
            for row in report.rows:
                if (
                    row.issuer == issuer.id
                    and row.issuer_name_as_reported
                    and base in name_key(row.issuer_name_as_reported)
                ):
                    found.append(
                        Support(
                            "issuer",
                            issuer.id,
                            "name",
                            f"breach report {report.document} row {row.row}",
                            report.document,
                        )
                    )
            for entry in report.no_information:
                if entry.issuer == issuer.id:
                    found.append(
                        Support(
                            "issuer",
                            issuer.id,
                            "identity",
                            f"no-information list of {report.document}",
                            report.document,
                        )
                    )
                    if base in name_key(entry.issuer_name_as_reported):
                        found.append(
                            Support(
                                "issuer",
                                issuer.id,
                                "name",
                                f"no-information list of {report.document}",
                                report.document,
                            )
                        )
        for census in dataset.monitoring_censuses.values():
            for entry in census.entries:
                held = dataset.instruments.get(entry.isin)
                if held is not None and held.issuer == issuer.id and base in name_key(entry.row_as_reported):
                    found.append(Support("issuer", issuer.id, "name", f"census {census.id}", census.document))
        for label, seen in observations:
            if base in name_key(seen.value_seen) and _concerns(dataset, label, issuer.id):
                found.append(Support("issuer", issuer.id, "name", label, observation=seen))
        for attribute in ("cin", "lei"):
            value = getattr(issuer, attribute)
            if not value:
                continue
            found += [
                Support("issuer", issuer.id, attribute, label, item.document)
                for label, item in anchors
                if item.quote and value in item.quote
            ]
            found += [
                Support("issuer", issuer.id, attribute, label, observation=seen)
                for label, seen in observations
                if value in seen.value_seen
            ]
    return found


def _concerns(dataset: Dataset, label: str, issuer_id: str) -> bool:
    """Whether an observation recorded under ``label`` is about this issuer or one of its instruments."""
    if label == f"issuer {issuer_id} observation":
        return True
    if label.startswith("instrument "):
        isin = label.split()[1]
        held = dataset.instruments.get(isin)
        return held is not None and held.issuer == issuer_id
    return False


def _printed_names(dataset: Dataset, issuer_id: str) -> Iterator[tuple[str, str]]:
    """Names a record prints for the issuer, with the document that prints them."""
    for report in dataset.breach_reports.values():
        for row in report.rows:
            if row.issuer == issuer_id and row.issuer_name_as_reported:
                yield row.issuer_name_as_reported, report.document
        for entry in report.no_information:
            if entry.issuer == issuer_id:
                yield entry.issuer_name_as_reported, report.document
    issuer = dataset.issuers[issuer_id]
    for variant in issuer.name_variants:
        for item in variant.evidence:
            yield variant.name, item.document


def as_of(dataset: Dataset, day: date, mode: AvailabilityMode = AvailabilityMode.ESTIMATED) -> Dataset:
    """The dataset as far as records shown public by ``day`` establish it, judged by the dates ``mode`` trusts.

    * Records whose document was not shown public by ``day`` are left out, and the evidence lists of those kept are
      cut to what was. Observations count from the day they were made.
    * An instrument is kept only if a record shown public by ``day`` prints its ISIN. An issuer is kept only if such a
      record supports it. Its name is the base name only if a record then public prints it, and otherwise the earliest
      name a record then public prints, or empty. Its CIN and LEI are kept only if a record then public prints them,
      and its sector never, since nothing in the record supports one.
    * Free-text notes, written with later knowledge, are dropped. Searches made after ``day`` are dropped, and so are
      reviews of annotations made after it; a clause record counts as reviewed only if reviews made by then settle it.

    The result holds nothing that tells what the full record contains beyond ``day``.
    """
    public_from = {doc_id: shown_public_by(doc, dataset, mode) for doc_id, doc in dataset.documents.items()}
    kept = {doc_id for doc_id, shown in public_from.items() if shown is not None and shown <= day}

    def visible(support: Support) -> bool:
        if support.observation is not None:
            return support.observation.observed_on <= day
        return support.document in kept

    def evidence(items: Iterable[Evidence]) -> list[Evidence]:
        return [item for item in items if item.document in kept]

    def observations(items: Iterable[Observation]) -> list[Observation]:
        return [item.model_copy(update={"note": None}) for item in items if item.observed_on <= day]

    established: dict[tuple[str, str, str], list[Support]] = {}
    for support in supports(dataset):
        if visible(support):
            established.setdefault((support.entity, support.key, support.attribute), []).append(support)

    instruments = {}
    for isin, held in dataset.instruments.items():
        if ("instrument", isin, "identity") not in established:
            continue
        claims = [
            claim.model_copy(
                update={
                    "evidence": evidence(claim.evidence),
                    "observations": observations(claim.observations),
                    "note": None,
                }
            )
            for claim in held.claims
            if evidence(claim.evidence) or observations(claim.observations)
        ]
        links = [
            link.model_copy(update={"evidence": evidence(link.evidence), "note": None})
            for link in held.documents
            if link.document in kept and evidence(link.evidence)
        ]
        instruments[isin] = held.model_copy(update={"claims": claims, "documents": links, "notes": None})

    issuers = {}
    for issuer_id, issuer in dataset.issuers.items():
        if ("issuer", issuer_id, "identity") not in established:
            continue
        if ("issuer", issuer_id, "name") in established:
            name = issuer.name
        else:
            printed = sorted(
                (public_from[document], text)
                for text, document in _printed_names(dataset, issuer_id)
                if document in kept
            )
            name = printed[0][1] if printed else ""
        issuers[issuer_id] = issuer.model_copy(
            update={
                "name": name,
                "cin": issuer.cin if ("issuer", issuer_id, "cin") in established else None,
                "lei": issuer.lei if ("issuer", issuer_id, "lei") in established else None,
                "sector": None,
                "name_variants": [
                    variant.model_copy(update={"evidence": evidence(variant.evidence)})
                    for variant in issuer.name_variants
                    if evidence(variant.evidence)
                ],
                "observations": observations(issuer.observations),
            }
        )

    def without_note(record, field: str = "notes"):
        return record.model_copy(update={field: None})

    reviews = []
    for review in dataset.reviews:
        if review.annotated_on > day:
            continue
        if review.adjudicated_on is not None and review.adjudicated_on > day:
            review = review.model_copy(
                update={
                    "adjudicated": None,
                    "adjudicated_by": None,
                    "adjudication_reason": None,
                    "adjudicated_on": None,
                }
            )
        reviews.append(review)
    reviewed = reviewed_records(replace(dataset, reviews=reviews))

    def provision(record: Provision) -> Provision:
        return record.model_copy(
            update={"notes": None, "annotation_reviewed": record.annotation_reviewed and record.id in reviewed}
        )

    return replace(
        dataset,
        documents={k: without_note(v) for k, v in dataset.documents.items() if k in kept},
        issuers=issuers,
        instruments=instruments,
        provisions={k: provision(v) for k, v in dataset.provisions.items() if v.document in kept},
        breach_reports={k: without_note(v) for k, v in dataset.breach_reports.items() if v.document in kept},
        breach_notices={k: without_note(v) for k, v in dataset.breach_notices.items() if v.document in kept},
        compliance_statements={
            k: without_note(v, "note") for k, v in dataset.compliance_statements.items() if v.document in kept
        },
        monitoring_censuses={
            k: without_note(v, "note") for k, v in dataset.monitoring_censuses.items() if v.document in kept
        },
        regulatory_references={k: v for k, v in dataset.regulatory_references.items() if v.document in kept},
        searches={k: v for k, v in dataset.searches.items() if v.performed_on <= day},
        discrepancies={
            k: v
            for k, v in dataset.discrepancies.items()
            if all(e.document in kept for e in v.evidence) and all(o.observed_on <= day for o in v.observations)
        },
        reviews=reviews,
        cutoff=day if dataset.cutoff is None else min(day, dataset.cutoff),
        availability_mode=mode,
    )
