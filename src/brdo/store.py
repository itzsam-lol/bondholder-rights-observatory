"""Loading the YAML dataset and checking its internal consistency.

Layout of the data directory::

    sources.yaml                 list of Source
    documents.yaml               list of Document
    issuers.yaml                 list of Issuer
    instruments/<ISIN>.yaml      one Instrument per file
    provisions/<document>.yaml   list of Provision quoted from that document
    breach-reports/<document>.yaml   one BreachReport per file
    breach-notices.yaml          list of BreachNotice
    compliance-statements.yaml   list of ComplianceStatement
    regulatory-references.yaml   list of RegulatoryReference
    searches.yaml                list of SearchRecord
    discrepancies.yaml           list of Discrepancy
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from brdo.fetch import source_for_url
from brdo.identifiers import isin_issuer_code
from brdo.models import (
    AnnotationReview,
    BreachNotice,
    BreachReport,
    ComplianceStatement,
    Discrepancy,
    Document,
    Evidence,
    Instrument,
    Issuer,
    MonitoringCensus,
    Provision,
    RegulatoryReference,
    SearchRecord,
    Source,
)
from brdo.vocab import (
    CONTRACT_DOCUMENT_TYPES,
    EXECUTED_CONTRACT_TYPES,
    OFFER_DOCUMENT_TYPES,
    TERM_STATING_DOCUMENT_TYPES,
    AvailabilityMode,
    DocumentType,
    ExcerptPolicy,
    InstrumentProperty,
    ProvisionStage,
    RedistributionPolicy,
    RetrievalPolicy,
    SourceKind,
)


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Problem:
    severity: Severity
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity}: {self.where}: {self.message}"


class DatasetError(Exception):
    """Raised when data files cannot be parsed into valid records."""

    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__("\n".join(str(problem) for problem in problems))


@dataclass
class Dataset:
    root: Path
    sources: dict[str, Source] = field(default_factory=dict)
    documents: dict[str, Document] = field(default_factory=dict)
    issuers: dict[str, Issuer] = field(default_factory=dict)
    instruments: dict[str, Instrument] = field(default_factory=dict)
    provisions: dict[str, Provision] = field(default_factory=dict)
    breach_reports: dict[str, BreachReport] = field(default_factory=dict)
    breach_notices: dict[str, BreachNotice] = field(default_factory=dict)
    compliance_statements: dict[str, ComplianceStatement] = field(default_factory=dict)
    monitoring_censuses: dict[str, MonitoringCensus] = field(default_factory=dict)
    regulatory_references: dict[str, RegulatoryReference] = field(default_factory=dict)
    searches: dict[str, SearchRecord] = field(default_factory=dict)
    discrepancies: dict[str, Discrepancy] = field(default_factory=dict)
    reviews: list[AnnotationReview] = field(default_factory=list)
    """Second annotations by people, with their adjudication (see ``review``)."""
    cutoff: date | None = None
    """Set on a point-in-time view (see ``pit.as_of``): the day whose public record the view holds."""
    availability_mode: AvailabilityMode | None = None
    """Which availability dates the point-in-time view trusted."""

    def source_of(self, document_id: str) -> Source:
        return self.sources[self.documents[document_id].source]

    def evidence(self) -> Iterator[tuple[str, Evidence]]:
        """Every document anchor in the dataset, with a label saying where it is used."""
        for issuer in self.issuers.values():
            for variant in issuer.name_variants:
                for item in variant.evidence:
                    yield f"issuer {issuer.id} name variant", item
        for instrument in self.instruments.values():
            for claim in instrument.claims:
                for item in claim.evidence:
                    yield f"instrument {instrument.isin} claim {claim.property}", item
            for link in instrument.documents:
                for item in link.evidence:
                    yield f"instrument {instrument.isin} link to {link.document}", item
        for provision in self.provisions.values():
            yield f"provision {provision.id}", provision.anchor()
        for report in self.breach_reports.values():
            for row in report.rows:
                label = f"breach report {report.document} row {row.row}"
                for anchor in row.anchors(report.document):
                    yield label, anchor
            for note in report.printed_notes:
                yield (
                    f"breach report {report.document} printed note",
                    Evidence(document=report.document, page=note.page, quote=note.text),
                )
            for entry in report.no_information:
                yield (
                    f"breach report {report.document} no-information list",
                    Evidence(document=report.document, page=entry.page, quote=entry.issuer_name_as_reported),
                )
        for notice in self.breach_notices.values():
            for anchor in notice.anchors():
                yield f"breach notice {notice.id}", anchor
        for statement in self.compliance_statements.values():
            for anchor in statement.anchors():
                yield f"compliance statement {statement.id}", anchor
        for census in self.monitoring_censuses.values():
            for anchor in census.anchors():
                yield f"monitoring census {census.id}", anchor
        for reference in self.regulatory_references.values():
            yield f"regulatory reference {reference.id}", reference.anchor()
        for discrepancy in self.discrepancies.values():
            for item in discrepancy.evidence:
                yield f"discrepancy {discrepancy.id}", item


def _read_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        try:
            return yaml.safe_load(handle)
        except yaml.YAMLError as error:
            raise DatasetError([Problem(Severity.ERROR, path.name, f"is not valid YAML: {error}")]) from error


def _parse[M: BaseModel](model: type[M], raw: Any, where: str, problems: list[Problem]) -> M | None:
    try:
        return model.model_validate(raw)
    except ValidationError as error:
        for detail in error.errors():
            location = ".".join(str(part) for part in detail["loc"])
            problems.append(Problem(Severity.ERROR, f"{where} {location}".strip(), detail["msg"]))
        return None


def _load_list[M: BaseModel](path: Path, model: type[M], problems: list[Problem]) -> list[M]:
    if not path.exists():
        return []
    raw = _read_yaml(path) or []
    if not isinstance(raw, list):
        problems.append(Problem(Severity.ERROR, str(path), "expected a list of records"))
        return []
    parsed = (_parse(model, item, f"{path.name}[{index}]", problems) for index, item in enumerate(raw))
    return [record for record in parsed if record is not None]


def _index[M: BaseModel](records: list[M], key: str, where: str, problems: list[Problem]) -> dict[str, M]:
    indexed: dict[str, M] = {}
    for record in records:
        identifier = getattr(record, key)
        if identifier in indexed:
            problems.append(Problem(Severity.ERROR, where, f"duplicate id {identifier}"))
        indexed[identifier] = record
    return indexed


def load_dataset(root: Path) -> Dataset:
    """Parse every data file; raise ``DatasetError`` if any record is invalid."""
    problems: list[Problem] = []
    dataset = Dataset(root=root)
    dataset.sources = _index(_load_list(root / "sources.yaml", Source, problems), "id", "sources", problems)
    dataset.documents = _index(_load_list(root / "documents.yaml", Document, problems), "id", "documents", problems)
    dataset.issuers = _index(_load_list(root / "issuers.yaml", Issuer, problems), "id", "issuers", problems)
    dataset.searches = _index(_load_list(root / "searches.yaml", SearchRecord, problems), "id", "searches", problems)
    dataset.discrepancies = _index(
        _load_list(root / "discrepancies.yaml", Discrepancy, problems), "id", "discrepancies", problems
    )
    dataset.breach_notices = _index(
        _load_list(root / "breach-notices.yaml", BreachNotice, problems), "id", "breach notices", problems
    )
    dataset.regulatory_references = _index(
        _load_list(root / "regulatory-references.yaml", RegulatoryReference, problems),
        "id",
        "regulatory references",
        problems,
    )
    dataset.compliance_statements = _index(
        _load_list(root / "compliance-statements.yaml", ComplianceStatement, problems),
        "id",
        "compliance statements",
        problems,
    )
    dataset.monitoring_censuses = _index(
        _load_list(root / "monitoring-censuses.yaml", MonitoringCensus, problems),
        "id",
        "monitoring censuses",
        problems,
    )
    dataset.reviews = _load_list(root / "annotation-reviews.yaml", AnnotationReview, problems)

    instruments = []
    for path in sorted((root / "instruments").glob("*.yaml")):
        instrument = _parse(Instrument, _read_yaml(path), path.name, problems)
        if instrument is None:
            continue
        if path.stem != instrument.isin:
            problems.append(Problem(Severity.ERROR, path.name, f"file name does not match ISIN {instrument.isin}"))
        instruments.append(instrument)
    dataset.instruments = _index(instruments, "isin", "instruments", problems)

    provisions = []
    for path in sorted((root / "provisions").glob("*.yaml")):
        for provision in _load_list(path, Provision, problems):
            if provision.document != path.stem:
                problems.append(
                    Problem(Severity.ERROR, path.name, f"{provision.id} quotes {provision.document}, not {path.stem}")
                )
            provisions.append(provision)
    dataset.provisions = _index(provisions, "id", "provisions", problems)

    reports = []
    for path in sorted((root / "breach-reports").glob("*.yaml")):
        report = _parse(BreachReport, _read_yaml(path), path.name, problems)
        if report is None:
            continue
        if report.document != path.stem:
            problems.append(Problem(Severity.ERROR, path.name, f"file name does not match {report.document}"))
        reports.append(report)
    dataset.breach_reports = _index(reports, "document", "breach reports", problems)

    if problems:
        raise DatasetError(problems)
    return dataset


def check_integrity(dataset: Dataset) -> list[Problem]:
    """Cross-record checks that single-record validation cannot express."""
    problems: list[Problem] = []

    def error(where: str, message: str) -> None:
        problems.append(Problem(Severity.ERROR, where, message))

    def warn(where: str, message: str) -> None:
        problems.append(Problem(Severity.WARNING, where, message))

    from brdo.pit import availability  # pit builds on this module, so it is imported here

    for document in dataset.documents.values():
        where = f"document {document.id}"
        found = availability(document, dataset)
        if found.dated_after_observation:
            error(where, f"carries a date after {found.confirmed_by}, the day it was retrieved")
        if found.estimate_precedes_own_date:
            warn(
                where,
                f"its server or publisher date precedes {found.not_before}, the latest date it or a letter in it "
                "gives; its availability is taken from that later date",
            )
        source = dataset.sources.get(document.source)
        if source is None:
            error(where, f"unknown source {document.source}")
            continue
        if source.retrieval is RetrievalPolicy.EXCLUDED or source.redistribution is RedistributionPolicy.NO_LINKS:
            error(where, f"source {source.id} may not be cited by URL under the project's source policy")
        if (
            document.retrieved_at is not None
            and not document.retrieved_manually
            and source.retrieval is not RetrievalPolicy.ALLOWED
        ):
            error(where, f"source {source.id} does not allow pipeline retrieval")
        for earlier in document.supersedes:
            previous = dataset.documents.get(earlier)
            if previous is None:
                error(where, f"supersedes unknown document {earlier}")
            elif (previous.source, previous.type) != (document.source, document.type):
                error(where, f"supersedes {earlier}, which is a different source or document type")

    clause_quotes = {(provision.document, provision.text) for provision in dataset.provisions.values()}
    for label, item in dataset.evidence():
        document = dataset.documents.get(item.document)
        if document is None:
            error(label, f"evidence cites unknown document {item.document}")
            continue
        if document.sha256 is None:
            error(label, f"evidence cites {item.document}, which has not been retrieved and hashed")
        if item.page is not None and document.pages is not None and item.page > document.pages:
            error(label, f"page {item.page} is beyond the {document.pages} pages of {item.document}")
        source = dataset.sources.get(document.source)
        if item.quote and source is not None and source.excerpts is ExcerptPolicy.NONE:
            error(label, f"quotes {item.document}, but source {source.id} allows no excerpts")
        if (
            item.quote
            and source is not None
            and len(item.quote) > source.quote_limit
            and (item.document, item.quote) not in clause_quotes
        ):
            error(label, f"quotes {len(item.quote)} characters of {source.id}, whose limit is {source.quote_limit}")

    issuer_codes: dict[str, set[str]] = {}
    for instrument in dataset.instruments.values():
        where = f"instrument {instrument.isin}"
        if instrument.issuer not in dataset.issuers:
            error(where, f"unknown issuer {instrument.issuer}")
        issuer_codes.setdefault(instrument.issuer, set()).add(isin_issuer_code(instrument.isin))
        for claim in instrument.claims:
            if claim.asserted_by not in dataset.sources:
                error(where, f"claim on {claim.property} asserted by unknown source {claim.asserted_by}")
            if claim.property is InstrumentProperty.DEBENTURE_TRUSTEE:
                named = dataset.sources.get(str(claim.value))
                if named is None or named.kind is not SourceKind.DEBENTURE_TRUSTEE:
                    error(where, f"trustee claim names {claim.value}, which is not a registered debenture trustee")
        for link in instrument.documents:
            if link.document not in dataset.documents:
                error(where, f"links unknown document {link.document}")
    for issuer, codes in issuer_codes.items():
        if len(codes) > 1:
            warn(f"issuer {issuer}", f"its ISINs carry different issuer codes {sorted(codes)}")

    for provision in dataset.provisions.values():
        where = f"provision {provision.id}"
        document = dataset.documents.get(provision.document)
        if document is not None and document.type not in TERM_STATING_DOCUMENT_TYPES:
            error(where, f"{provision.document} is a {document.type}, which cannot state a contractual term")
        stage_types = {
            ProvisionStage.EXECUTED_TEXT: EXECUTED_CONTRACT_TYPES,
            ProvisionStage.OFFERED: OFFER_DOCUMENT_TYPES,
        }
        if (
            document is not None
            and provision.stage in stage_types
            and document.type not in stage_types[provision.stage]
        ):
            error(where, f"is marked {provision.stage}, but {provision.document} is a {document.type}")
        if provision.amends is not None and provision.amends not in dataset.provisions:
            error(where, f"amends unknown provision {provision.amends}")
        for isin in provision.instruments:
            instrument = dataset.instruments.get(isin)
            if instrument is None:
                error(where, f"governs unknown instrument {isin}")
            elif (
                document is not None
                and document.type in CONTRACT_DOCUMENT_TYPES
                and provision.document not in {link.document for link in instrument.documents}
            ):
                warn(where, f"{isin} has no document link to its contract {provision.document}")

    for report in dataset.breach_reports.values():
        where = f"breach report {report.document}"
        document = dataset.documents.get(report.document)
        if document is not None:
            if document.type is not DocumentType.TRUSTEE_BREACH_STATUS_REPORT:
                error(where, f"{report.document} is a {document.type}, not a breach status report")
            if document.source != report.trustee:
                error(where, f"document is published by {document.source}, not by {report.trustee}")
        trustee = dataset.sources.get(report.trustee)
        if trustee is None or trustee.kind is not SourceKind.DEBENTURE_TRUSTEE:
            error(where, f"{report.trustee} is not a debenture trustee source")
        for entry in report.no_information:
            if entry.issuer is not None and entry.issuer not in dataset.issuers:
                error(where, f"no-information entry names unknown issuer {entry.issuer}")
        for row in report.rows:
            row_where = f"{where} row {row.row}"
            if row.issuer not in dataset.issuers:
                error(row_where, f"unknown issuer {row.issuer}")
            for item in row.items:
                for isin in item.isins:
                    instrument = dataset.instruments.get(isin)
                    if instrument is None:
                        error(row_where, f"lists {isin}, which has no instrument record")
                    elif instrument.issuer != row.issuer:
                        error(row_where, f"{isin} belongs to {instrument.issuer}, not {row.issuer}")
                for link in item.provisions:
                    provision = dataset.provisions.get(link.provision)
                    if provision is None:
                        error(row_where, f"links unknown provision {link.provision}")
                    elif not set(provision.instruments) & set(item.isins):
                        warn(row_where, f"provision {link.provision} governs none of {item.isins}")

    for notice in dataset.breach_notices.values():
        where = f"breach notice {notice.id}"
        if notice.document not in dataset.documents:
            error(where, f"unknown document {notice.document}")
        if notice.trustee not in dataset.sources:
            error(where, f"unknown trustee {notice.trustee}")
        for isin in notice.isins:
            if isin not in dataset.instruments:
                error(where, f"names {isin}, which has no instrument record")

    for statement in dataset.compliance_statements.values():
        where = f"compliance statement {statement.id}"
        if statement.stated_by not in dataset.sources:
            error(where, f"unknown source {statement.stated_by}")
        if statement.document not in dataset.documents:
            error(where, f"unknown document {statement.document}")
        for isin in statement.instruments:
            if isin not in dataset.instruments:
                error(where, f"unknown instrument {isin}")

    for census in dataset.monitoring_censuses.values():
        where = f"monitoring census {census.id}"
        if census.document not in dataset.documents:
            error(where, f"unknown document {census.document}")
        trustee = dataset.sources.get(census.trustee)
        if trustee is None or trustee.kind is not SourceKind.DEBENTURE_TRUSTEE:
            error(where, f"{census.trustee} is not a registered debenture trustee")

    for search in dataset.searches.values():
        for document_id in search.documents:
            if document_id not in dataset.documents:
                error(f"search {search.id}", f"unknown document {document_id}")

    cited = {item.document for _, item in dataset.evidence()} | set(dataset.breach_reports)
    cited |= {notice.document for notice in dataset.breach_notices.values()}
    for document_id in dataset.documents:
        if document_id not in cited:
            warn(f"document {document_id}", "no record cites it")

    no_links = [source for source in dataset.sources.values() if source.redistribution is RedistributionPolicy.NO_LINKS]
    published_urls = [(f"search {s.id}", url) for s in dataset.searches.values() for url in s.urls_seen]
    published_urls += [(f"issuer {i.id}", o.url) for i in dataset.issuers.values() for o in i.observations]
    published_urls += [
        (f"instrument {i.isin}", o.url) for i in dataset.instruments.values() for c in i.claims for o in c.observations
    ]
    published_urls += [(f"discrepancy {d.id}", o.url) for d in dataset.discrepancies.values() for o in d.observations]
    for where, url in published_urls:
        source = source_for_url(url, no_links)
        if source is not None:
            error(where, f"carries a link to {source.id}, whose policy forbids links")

    from brdo.review import review_problems  # review reads records through this module's Dataset

    for where, message in review_problems(dataset):
        error(where, message)

    return problems
