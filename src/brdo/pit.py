"""Point-in-time views: what the reviewed public record established on a given date.

A historical view must not expose anything that the evidence available on its date did not establish. That needs
three things this module keeps explicit.

**When a file was public is uncertain, and the record keeps the kinds of evidence apart.**

* A lower bound. A file cannot have been public before the latest date it gives itself, before a letter it
  contains was dated, before the latest event it records, or before the period it reports on began. This assumes
  those dates are right.
* A publisher's own date, such as a listing page's date: the publisher's claim about when it posted the file.
* The server's Last-Modified date, which dates the version of the file the server held. It is not the file's
  first publication: a file can be uploaded before it is linked, replaced, or copied with a misleading date.
* The day the project retrieved the file from its public address. That proves the file was public by then. It is
  usually much later than first publication.

On any day a file is in one of three states (``AvailabilityState``): not yet possible, before a lower bound;
confirmed, once the project had observed it; and uncertain in between. The publisher's and the server's dates do
not settle an uncertain day. They give an estimate, the later of the two and never before the lower bound, which is
an assumption about when this exact file was at its address, not evidence that it was. A file with neither date has
no estimate.

**Views are built under a stated rule** (``AvailabilityMode``) and nest: ``observed`` admits only what the project
had itself observed; ``estimated`` also admits uncertain files whose estimate has passed; ``possible`` admits every
file no lower bound rules out. Each view records, for every file it admits, whether that file was confirmed or only
uncertain on the day, so that what rests on evidence can be told from what rests on the estimate.

**Entities and attributes need support** (``supports``), with the kind of evidence named (``SupportBasis``). An ISIN
appears in a view only if a record then admitted prints it. The issuer it belongs to, the issuer's name, its CIN and
its LEI each need their own support: a record printing the ISIN does not by itself show whose it is. Where the view
cannot show which issuer an ISIN belongs to, or cannot tell an issuer from another of the same name, it refers to
the issuer by the issuer code that the ISINs themselves print, never by the dataset's identifier, which encodes the
name. Free-text notes and descriptions written later are dropped, and so are searches and reviews made after the
date. Nothing in a view says what the full record holds beyond it.

A test can show that these rules are applied consistently. It cannot show that the dates the rules use are
historically right: a wrong Last-Modified header gives a consistently wrong estimated view.
"""

import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace
from datetime import date

from brdo.identifiers import isin_issuer_code
from brdo.models import Document, Evidence, Issuer, Observation
from brdo.pdftext import normalize
from brdo.review import reviewed_records
from brdo.store import Dataset
from brdo.vocab import AvailabilityMode, AvailabilityState, DocumentDateKind, SupportBasis

OWN_DATE_BASIS = "not before its own date"
CONFIRMED_BASIS = "observed by the project"
NO_ESTIMATE_BASIS = "no publisher or server date"


@dataclass(frozen=True)
class Availability:
    """What the record shows about when one exact file was public. Only ``confirmed_by`` is proved by the record."""

    not_before: date | None
    """Lower bound: the file cannot have been public before this day, if the dates it prints are right."""
    not_before_basis: str
    estimate: date | None
    """The later of the publisher's and the server's dates, never before the lower bound. An assumption about when
    this exact file was at its address, not evidence that it was, and not a publication date."""
    estimate_basis: str
    confirmed_by: date | None
    """The project retrieved the file from its public address on this day, so it was public by then."""
    confirmed_basis: str
    last_modified: date | None = None
    published: date | None = None
    """The publisher's own date for the file, such as a listing page's."""

    def state_on(self, day: date) -> AvailabilityState:
        """Whether, on ``day``, the file was confirmed public, ruled out by a lower bound, or neither."""
        if self.confirmed_by is not None and day >= self.confirmed_by:
            return AvailabilityState.CONFIRMED
        if self.not_before is not None and day < self.not_before:
            return AvailabilityState.NOT_YET_POSSIBLE
        return AvailabilityState.UNCERTAIN

    def admitted_from(self, mode: AvailabilityMode) -> date | None:
        """The first day a view of ``mode`` admits the file, or None if it never does."""
        if mode is AvailabilityMode.OBSERVED:
            return self.confirmed_by
        if mode is AvailabilityMode.POSSIBLE:
            return self.not_before or date.min
        return min((d for d in (self.estimate, self.confirmed_by) if d is not None), default=None)

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
    if document.period is not None:
        bounds.append((document.period.start, "the start of the period it reports on"))
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
    for census in dataset.monitoring_censuses.values():
        if census.document == document.id:
            bounds += [
                (entry.received.value, "an event it reports")
                for entry in census.entries
                if entry.received is not None and entry.received.value is not None
            ]
    return bounds


def availability(document: Document, dataset: Dataset | None = None) -> Availability:
    """The evidence on when this exact file was public, kept apart, with an estimate and how each is known.

    With ``dataset``, the dates of letters transcribed from the file and of events it records also bound it from
    below. A file with neither a publisher's nor a server's date has no estimate: unknown stays unknown.
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
    estimate: date | None = None
    estimate_basis = NO_ESTIMATE_BASIS
    if candidates:
        # The later of the two: neither the publisher nor the server suggests that this exact version was at its
        # address before its own date. Ties keep the publisher's date. Neither can establish first publication.
        estimate, estimate_basis = max(candidates, key=lambda candidate: candidate[0])
        if not_before is not None and estimate < not_before:
            estimate, estimate_basis = not_before, f"not before {not_before_basis}"
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


def shown_public_by(document: Document, dataset: Dataset, mode: AvailabilityMode) -> date | None:
    """The first day a view of ``mode`` admits this file."""
    return availability(document, dataset).admitted_from(mode)


@dataclass(frozen=True)
class Support:
    """A record that supports one attribute of an instrument or issuer, with the kind of evidence it is.

    ``attribute`` is ``identity`` (the ISIN) or ``issuer`` (whose it is) for an instrument, and ``identity``,
    ``name``, ``cin`` or ``lei`` for an issuer. ``matched`` is the value as the source prints it, such as the ISIN,
    the name or the identifier, and is the source's text; ``explanation`` is the project's account of why the rule
    applies. Only bases in ``ESTABLISHING_BASES`` establish anything in a view.
    """

    entity: str
    key: str
    attribute: str
    record: str
    basis: SupportBasis
    document: str | None = None
    observation: Observation | None = None
    matched: str = ""
    explanation: str = ""

    @property
    def establishes(self) -> bool:
        from brdo.vocab import ESTABLISHING_BASES

        return self.basis in ESTABLISHING_BASES


_ABBREVIATIONS = ((r"\bltd\b\.?", "limited"), (r"\bpvt\b\.?", "private"), (r"&", " and "), (r"[^a-z0-9 ]", " "))
_PARENTHESIS = re.compile(r"^(?P<name>.+?)\s*\((?P<addition>[^()]+)\)\s*$")
_URL_ISIN = re.compile(r"[?&]ISIN=([A-Z0-9]{12})\b", re.IGNORECASE)


def name_key(name: str) -> str:
    """A name folded for matching: case, punctuation, and "Ltd"/"Pvt" against "Limited"/"Private"."""
    text = normalize(name)
    for pattern, replacement in _ABBREVIATIONS:
        text = re.sub(pattern, replacement, text)
    return " ".join(text.split())


def match_name(printed: str, issuer: Issuer) -> SupportBasis | None:
    """How a printed name matches the issuer: exactly, with a parenthetical addition, as a recorded variant, or not.

    The comparison is of whole names, never of one name contained in another, so "Finance Limited" cannot match
    "Aye Finance Limited".
    """
    printed_key = name_key(printed)
    if printed_key == name_key(issuer.name):
        return SupportBasis.EXACT_NAME
    parenthesis = _PARENTHESIS.match(printed.strip())
    if parenthesis and name_key(parenthesis.group("name")) == name_key(issuer.name):
        return SupportBasis.NAME_WITH_ADDITION
    variants = {name_key(variant.name) for variant in issuer.name_variants}
    if printed_key in variants or (parenthesis and name_key(parenthesis.group("name")) in variants):
        return SupportBasis.NAME_VARIANT
    return None


def _quote_names(quote: str, issuer: Issuer, dataset: Dataset) -> bool:
    """Whether a longer quotation contains the issuer's full name, and no longer name of another issuer around it."""
    text = f" {name_key(quote)} "
    names = {name_key(issuer.name)} | {name_key(variant.name) for variant in issuer.name_variants}
    if not any(f" {name} " in text for name in names if name):
        return False
    others = {name_key(other.name) for other in dataset.issuers.values() if other.id != issuer.id}
    return not any(f" {other} " in text and any(name in other for name in names) for other in others)


def shared_names(dataset: Dataset) -> dict[str, set[str]]:
    """For each issuer, the other issuers in the dataset with the same name. A shared name identifies neither."""
    by_name: dict[str, set[str]] = defaultdict(set)
    for issuer in dataset.issuers.values():
        by_name[name_key(issuer.name)].add(issuer.id)
    return {issuer_id: by_name[name_key(issuer.name)] - {issuer_id} for issuer_id, issuer in dataset.issuers.items()}


def _url_isin(url: str) -> str | None:
    found = _URL_ISIN.search(url)
    return found.group(1).upper() if found else None


def _identity_supports(dataset: Dataset) -> Iterator[Support]:
    """Records that print an ISIN of the dataset's instruments, with how the printing is evidenced."""

    def instrument(isin: str, record: str, basis: SupportBasis, explanation: str, document=None, observation=None):
        if isin in dataset.instruments:
            matched = isin if basis is not SupportBasis.FLAG_ONLY else ""
            yield Support("instrument", isin, "identity", record, basis, document, observation, matched, explanation)

    page_names_isin = "the depository page's address names the ISIN"
    for isin, held in dataset.instruments.items():
        for claim in held.claims:
            label = f"claim {claim.property} by {claim.asserted_by}"
            for item in claim.evidence:
                if item.quote and isin in item.quote:
                    yield from instrument(
                        isin, label, SupportBasis.QUOTED, "printed in the claim's quotation", item.document
                    )
            for seen in claim.observations:
                if _url_isin(seen.url) == isin or isin in seen.value_seen:
                    why = page_names_isin if _url_isin(seen.url) == isin else "the observed value prints the ISIN"
                    yield from instrument(isin, label, SupportBasis.OBSERVED, why, observation=seen)
        for link in held.documents:
            for item in link.evidence:
                if item.quote and isin in item.quote:
                    why = "printed in the link's quotation"
                    yield from instrument(isin, f"link to {link.document}", SupportBasis.QUOTED, why, item.document)
    for issuer in dataset.issuers.values():
        for seen in issuer.observations:
            isin = _url_isin(seen.url)
            if isin is not None:
                label = f"issuer {issuer.id} observation"
                yield from instrument(isin, label, SupportBasis.OBSERVED, page_names_isin, observation=seen)
    for report in dataset.breach_reports.values():
        for row in report.rows:
            for isin in row.isins:
                label = f"breach report {report.document} row {row.row}"
                yield from instrument(isin, label, SupportBasis.QUOTED, "printed in the row", report.document)
    for notice in dataset.breach_notices.values():
        if notice.isins_printed:
            for isin in notice.isins:
                yield from instrument(
                    isin, f"letter {notice.id}", SupportBasis.QUOTED, "printed in the letter", notice.document
                )
    for statement in dataset.compliance_statements.values():
        label = f"statement {statement.id}"
        printed = {isin for line in statement.exceptions for isin in line.isins}
        quoted = {isin for item in statement.evidence for isin in statement.instruments if isin in (item.quote or "")}
        for isin in sorted(printed | quoted):
            yield from instrument(isin, label, SupportBasis.QUOTED, "printed in the statement", statement.document)
        if statement.isins_printed:
            for isin in sorted(set(statement.instruments) - printed - quoted):
                why = "isins_printed is set, but no anchor quotes this ISIN"
                yield from instrument(isin, label, SupportBasis.FLAG_ONLY, why, statement.document)
    for census in dataset.monitoring_censuses.values():
        label = f"census {census.id}"
        quoted = {entry.isin for entry in census.entries if entry.isin in entry.row_as_reported}
        for isin in sorted(quoted):
            yield from instrument(isin, label, SupportBasis.QUOTED, "printed in the census row", census.document)
        for isin in sorted((set(census.sample) | set(census.report_not_received)) - quoted):
            why = "in an ISIN list recomputed from the file's text"
            yield from instrument(isin, label, SupportBasis.RECOMPUTED, why, census.document)


def _relationship_supports(dataset: Dataset, identity: list[Support]) -> Iterator[Support]:
    """Records that show which issuer an ISIN belongs to. Printing the ISIN alone does not."""

    def link(
        isin: str, record: str, basis: SupportBasis, matched: str, explanation: str, document=None, observation=None
    ):
        yield Support("instrument", isin, "issuer", record, basis, document, observation, matched, explanation)

    owner = {isin: held.issuer for isin, held in dataset.instruments.items()}
    for report in dataset.breach_reports.values():
        for row in report.rows:
            issuer = dataset.issuers.get(row.issuer)
            printed = row.issuer_name_as_reported
            if issuer is None or not printed or match_name(printed, issuer) is None:
                continue
            for isin in row.isins:
                if owner.get(isin) == issuer.id:
                    label = f"breach report {report.document} row {row.row}"
                    why = "the row prints this name with the ISIN"
                    yield from link(isin, label, SupportBasis.PRINTED_WITH_NAME, printed, why, report.document)
    for isin, held in dataset.instruments.items():
        issuer = dataset.issuers.get(held.issuer)
        if issuer is None:
            continue
        for claim in held.claims:
            for item in claim.evidence:
                if item.quote and isin in item.quote and _quote_names(item.quote, issuer, dataset):
                    label = f"claim {claim.property} by {claim.asserted_by}"
                    why = "the claim's quotation prints the issuer's name with the ISIN"
                    yield from link(isin, label, SupportBasis.PRINTED_WITH_NAME, item.quote, why, item.document)
    for notice in dataset.breach_notices.values():
        if not notice.isins_printed:
            continue
        quotes = [notice.deed_as_reported, notice.covenant_as_reported, notice.issuer_intimation_as_reported]
        for isin in notice.isins:
            issuer = dataset.issuers.get(owner.get(isin, ""))
            if issuer is None:
                continue
            named = [quote for quote in quotes if quote and _quote_names(quote, issuer, dataset)]
            label = f"letter {notice.id}"
            if named:
                why = "a quotation from the letter prints the issuer's name"
                yield from link(isin, label, SupportBasis.PRINTED_WITH_NAME, named[0], why, notice.document)
            else:
                why = "a trustee's letter to the ISIN's holders; no transcribed quotation prints the issuer's name"
                yield from link(isin, label, SupportBasis.LETTER_TO_HOLDERS, "", why, notice.document)
    publisher = {source.id: source.issuer for source in dataset.sources.values() if source.issuer}
    for support in identity:
        if support.document is None or support.basis not in (SupportBasis.QUOTED, SupportBasis.RECOMPUTED):
            continue
        document = dataset.documents.get(support.document)
        if document is not None and publisher.get(document.source) == owner.get(support.key):
            why = f"published on {document.source}, the issuer's own website"
            basis = SupportBasis.ISSUER_PUBLICATION
            yield from link(support.key, support.record, basis, support.key, why, support.document)
    for issuer in dataset.issuers.values():
        for seen in issuer.observations:
            isin = _url_isin(seen.url)
            if isin is not None and owner.get(isin) == issuer.id and match_name(seen.value_seen.split(";")[0], issuer):
                label = f"issuer {issuer.id} observation"
                why = "the depository page for the ISIN shows the issuer"
                yield from link(
                    isin, label, SupportBasis.OBSERVED, seen.value_seen.split(";")[0], why, observation=seen
                )


def _issuer_support(
    issuer_id: str,
    attribute: str,
    record: str,
    basis: SupportBasis,
    matched: str,
    explanation: str,
    document=None,
    observation=None,
) -> Support:
    return Support("issuer", issuer_id, attribute, record, basis, document, observation, matched, explanation)


def _issuer_supports(dataset: Dataset) -> Iterator[Support]:
    """Records that identify an issuer, print its name, or print its CIN or LEI for it."""
    publisher = {source.id: source.issuer for source in dataset.sources.values() if source.issuer}
    anchors = list(dataset.evidence())
    for issuer in dataset.issuers.values():
        printed: list[tuple[str, str, str]] = []
        for report in dataset.breach_reports.values():
            for row in report.rows:
                if row.issuer == issuer.id and row.issuer_name_as_reported:
                    label = f"breach report {report.document} row {row.row}"
                    printed.append((row.issuer_name_as_reported, label, report.document))
            for entry in report.no_information:
                if entry.issuer == issuer.id:
                    printed.append(
                        (entry.issuer_name_as_reported, f"no-information list of {report.document}", report.document)
                    )
        for text, record, document in printed:
            basis = match_name(text, issuer)
            if basis is None:
                continue
            why = (
                "a recorded variant of the name is printed"
                if basis is SupportBasis.NAME_VARIANT
                else "the name is printed"
            )
            yield _issuer_support(issuer.id, "identity", record, basis, text, why, document)
            if basis is not SupportBasis.NAME_VARIANT:
                yield _issuer_support(issuer.id, "name", record, basis, text, why, document)
        for variant in issuer.name_variants:
            for item in variant.evidence:
                why = "a recorded variant of the name, with its own evidence"
                yield _issuer_support(
                    issuer.id,
                    "identity",
                    f"issuer {issuer.id} name variant",
                    SupportBasis.NAME_VARIANT,
                    variant.name,
                    why,
                    item.document,
                )
        for seen in issuer.observations:
            name = seen.value_seen.split(";")[0]
            basis = match_name(name, issuer)
            if basis is None:
                continue
            label, why = f"issuer {issuer.id} observation", "the issuer's depository page shows the name"
            yield _issuer_support(issuer.id, "identity", label, SupportBasis.OBSERVED, name, why, observation=seen)
            if basis is not SupportBasis.NAME_VARIANT:
                yield _issuer_support(issuer.id, "name", label, SupportBasis.OBSERVED, name, why, observation=seen)
        for document in dataset.documents.values():
            if publisher.get(document.source) == issuer.id:
                why = f"published on {document.source}, the issuer's own website"
                label = f"document {document.id}"
                yield _issuer_support(
                    issuer.id, "identity", label, SupportBasis.ISSUER_PUBLICATION, "", why, document.id
                )
        for attribute in ("cin", "lei"):
            value = getattr(issuer, attribute)
            if not value:
                continue
            for label, item in anchors:
                if not item.quote or value not in item.quote:
                    continue
                document = dataset.documents.get(item.document)
                if document is not None and publisher.get(document.source) == issuer.id:
                    basis, why = SupportBasis.ISSUER_PUBLICATION, "printed in the issuer's own publication"
                elif _quote_names(item.quote, issuer, dataset):
                    basis, why = SupportBasis.QUOTED, "printed in a quotation that also names the issuer"
                else:
                    continue
                yield _issuer_support(issuer.id, attribute, label, basis, value, why, item.document)
                yield _issuer_support(issuer.id, "identity", label, basis, value, why, item.document)
            for seen in issuer.observations:
                if value in seen.value_seen:
                    why = "shown on the depository page for one of its ISINs"
                    label = f"issuer {issuer.id} observation"
                    yield _issuer_support(
                        issuer.id, attribute, label, SupportBasis.OBSERVED, value, why, observation=seen
                    )


def supports(dataset: Dataset) -> list[Support]:
    """Every record that supports an instrument's identity or issuer, or an issuer's identity, name, CIN or LEI.

    Each support names its basis. An instrument's identity needs a record that prints the ISIN. Which issuer the
    ISIN belongs to needs a record that prints the issuer's name with it, the issuer's own publication of it, or a
    depository page for it that shows the issuer; a trustee's letter that only prints the ISIN is recorded, labelled,
    but does not establish the link. An issuer's identity needs its name, a recorded variant, its CIN or LEI, or a
    publication on its own website. Names match as whole names, exactly or with a parenthetical addition. A CIN or
    LEI counts only where the quotation is the issuer's own publication or also prints the issuer's name, or where a
    depository page for one of its ISINs shows it.
    """
    identity = list(_identity_supports(dataset))
    found = identity + list(_relationship_supports(dataset, identity)) + list(_issuer_supports(dataset))
    seen: set[tuple] = set()
    unique: list[Support] = []
    for support in found:
        key = (
            support.entity,
            support.key,
            support.attribute,
            support.record,
            support.basis,
            support.document,
            support.observation.url if support.observation else None,
        )
        if key not in seen:
            seen.add(key)
            unique.append(support)
    return unique


def code_owners(dataset: Dataset) -> dict[str, set[str]]:
    """For each ISIN issuer code, the issuers of the dataset whose ISINs carry it."""
    owners: dict[str, set[str]] = defaultdict(set)
    for isin, held in dataset.instruments.items():
        owners[isin_issuer_code(isin)].add(held.issuer)
    return owners


def placeholder_issuer(code: str) -> str:
    """How a view refers to an issuer it cannot identify: by the issuer code its ISINs print."""
    return f"issuer-code-{code.lower()}"


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


_RELATIONSHIP_STRENGTH = (
    SupportBasis.PRINTED_WITH_NAME,
    SupportBasis.ISSUER_PUBLICATION,
    SupportBasis.OBSERVED,
    SupportBasis.ISSUER_CODE,
)


def as_of(dataset: Dataset, day: date, mode: AvailabilityMode = AvailabilityMode.ESTIMATED) -> Dataset:
    """The dataset as far as records admitted by ``day`` under ``mode`` establish it.

    * Records whose document the mode does not admit by ``day`` are left out, and the evidence lists of those kept
      are cut to what was admitted. Observations count from the day they were made. ``availability_states`` says, for
      each admitted file, whether it was confirmed public on ``day`` or only uncertain.
    * An instrument is kept only if an admitted record prints its ISIN. Its issuer is shown only if an admitted record
      establishes the link (``relationship_bases`` names how), and otherwise by the issuer code its ISIN prints.
    * An issuer is kept only if an admitted record identifies it. It keeps the dataset's identifier only if it can be
      told from every other issuer: by a name no other issuer shares, its CIN or LEI, or its own website. Otherwise it
      appears under the issuer code of its ISINs. Its name is its base name only if an admitted record prints it, and
      otherwise the earliest name an admitted record prints, or empty. Its CIN and LEI appear only if an admitted
      record prints them for it, and its sector never.
    * ISINs that a record lists but no admitted record prints are removed from it.
    * Free-text notes and discrepancy descriptions, written with later knowledge, are dropped. Searches and reviews
      of annotations made after ``day`` are dropped; a clause record counts as reviewed only if reviews made by then
      settle it.

    The result holds nothing that tells what the full record contains beyond ``day``.
    """
    found = {doc_id: availability(doc, dataset) for doc_id, doc in dataset.documents.items()}
    kept = {
        doc_id for doc_id, held in found.items() if (start := held.admitted_from(mode)) is not None and start <= day
    }
    states = {doc_id: found[doc_id].state_on(day) for doc_id in sorted(kept)}

    def visible(support: Support) -> bool:
        if not support.establishes:
            return False
        if support.observation is not None:
            return support.observation.observed_on <= day
        return support.document in kept

    def evidence(items: Iterable[Evidence]) -> list[Evidence]:
        return [item for item in items if item.document in kept]

    def observations(items: Iterable[Observation]) -> list[Observation]:
        return [item.model_copy(update={"note": None}) for item in items if item.observed_on <= day]

    established: dict[tuple[str, str, str], list[Support]] = defaultdict(list)
    for support in supports(dataset):
        if visible(support):
            established[(support.entity, support.key, support.attribute)].append(support)

    present = {isin for isin in dataset.instruments if ("instrument", isin, "identity") in established}
    relationship: dict[str, SupportBasis | None] = {}
    for isin in sorted(present):
        bases = {support.basis for support in established.get(("instrument", isin, "issuer"), [])}
        relationship[isin] = next((basis for basis in _RELATIONSHIP_STRENGTH if basis in bases), None)
    owners = code_owners(dataset)
    for isin in sorted(present):
        if relationship[isin] is not None:
            continue
        code, issuer_id = isin_issuer_code(isin), dataset.instruments[isin].issuer
        if owners[code] == {issuer_id} and any(
            other != isin
            and isin_issuer_code(other) == code
            and relationship.get(other) not in (None, SupportBasis.ISSUER_CODE)
            for other in present
        ):
            relationship[isin] = SupportBasis.ISSUER_CODE

    others_named = shared_names(dataset)
    view_id: dict[str, str] = {}
    issuers: dict[str, Issuer] = {}
    for issuer_id, issuer in dataset.issuers.items():
        if ("issuer", issuer_id, "identity") not in established:
            continue
        identified = any(("issuer", issuer_id, attribute) in established for attribute in ("cin", "lei"))
        published = any(
            s.basis is SupportBasis.ISSUER_PUBLICATION for s in established[("issuer", issuer_id, "identity")]
        )
        if ("issuer", issuer_id, "name") in established:
            name = issuer.name
        else:
            printed = sorted(
                (found[document].admitted_from(mode) or date.min, text)
                for text, document in _printed_names(dataset, issuer_id)
                if document in kept
            )
            name = printed[0][1] if printed else ""
        record = issuer.model_copy(
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
        if not others_named[issuer_id] or identified or published:
            view_id[issuer_id] = issuer_id
            issuers[issuer_id] = record
            continue
        codes = sorted({isin_issuer_code(isin) for isin in present if dataset.instruments[isin].issuer == issuer_id})
        for code in codes:
            issuers[placeholder_issuer(code)] = record.model_copy(
                update={"id": placeholder_issuer(code), "name_variants": []}
            )

    def issuer_ref(issuer_id: str, isin: str) -> str:
        return view_id.get(issuer_id) or placeholder_issuer(isin_issuer_code(isin))

    instruments = {}
    for isin in sorted(present):
        held = dataset.instruments[isin]
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
        target = (
            issuer_ref(held.issuer, isin)
            if relationship[isin] is not None
            else placeholder_issuer(isin_issuer_code(isin))
        )
        instruments[isin] = held.model_copy(
            update={"issuer": target, "claims": claims, "documents": links, "notes": None}
        )

    def without_note(record, field: str = "notes"):
        return record.model_copy(update={field: None})

    def listed(isins: Iterable[str]) -> list[str]:
        return [isin for isin in isins if isin in present]

    reports = {}
    for key, report in dataset.breach_reports.items():
        if report.document not in kept:
            continue
        rows = [
            row.model_copy(update={"issuer": issuer_ref(row.issuer, row.isins[0]) if row.isins else row.issuer})
            for row in report.rows
        ]
        entries = [
            entry.model_copy(update={"issuer": view_id.get(entry.issuer or "")}) for entry in report.no_information
        ]
        reports[key] = report.model_copy(update={"rows": rows, "no_information": entries, "notes": None})

    notices = {}
    for key, notice in dataset.breach_notices.items():
        if notice.document in kept and listed(notice.isins):
            notices[key] = notice.model_copy(update={"isins": listed(notice.isins), "notes": None})

    provisions = {}
    for key, provision in dataset.provisions.items():
        if provision.document in kept and listed(provision.instruments):
            provisions[key] = provision.model_copy(update={"instruments": listed(provision.instruments), "notes": None})

    statements = {}
    for key, statement in dataset.compliance_statements.items():
        if statement.document not in kept or not listed(statement.instruments):
            continue
        lines = [
            line.model_copy(update={"isins": listed(line.isins)}) for line in statement.exceptions if listed(line.isins)
        ]
        statements[key] = statement.model_copy(
            update={"instruments": listed(statement.instruments), "exceptions": lines, "note": None}
        )

    censuses = {
        key: census.model_copy(update={"listed_not_printed": listed(census.listed_not_printed), "note": None})
        for key, census in dataset.monitoring_censuses.items()
        if census.document in kept
    }

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
    provisions = {
        key: provision.model_copy(
            update={"annotation_reviewed": provision.annotation_reviewed and provision.id in reviewed}
        )
        for key, provision in provisions.items()
    }

    def subject(text: str) -> str:
        if text in dataset.issuers:
            return view_id.get(text, "")
        return text

    return replace(
        dataset,
        documents={k: without_note(v) for k, v in dataset.documents.items() if k in kept},
        issuers=issuers,
        instruments=instruments,
        provisions=provisions,
        breach_reports=reports,
        breach_notices=notices,
        compliance_statements=statements,
        monitoring_censuses=censuses,
        regulatory_references={k: v for k, v in dataset.regulatory_references.items() if v.document in kept},
        searches={
            k: v.model_copy(update={"subject": subject(v.subject), "note": None})
            for k, v in dataset.searches.items()
            if v.performed_on <= day
        },
        discrepancies={
            k: v.model_copy(update={"subject": subject(v.subject), "description": "", "resolution": None})
            for k, v in dataset.discrepancies.items()
            if all(e.document in kept for e in v.evidence) and all(o.observed_on <= day for o in v.observations)
        },
        reviews=reviews,
        cutoff=day if dataset.cutoff is None else min(day, dataset.cutoff),
        availability_mode=mode,
        availability_states=states,
        relationship_bases=relationship,
    )
