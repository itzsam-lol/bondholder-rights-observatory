"""Record types of the dataset.

The dataset is a set of attributed statements, not a table of facts. Every
statement names who made it and points at the evidence: a retrieved document,
a page in it and the words relied on. Interpretation added by the project
(classifications, parsed dates, links between a reported breach and a contract
clause) is held in separately named fields so it is never confused with what a
source actually said.
"""

from collections.abc import Iterator
from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from brdo.dates import find_printed_dates, parse_printed_date
from brdo.identifiers import is_valid_cin, is_valid_isin, is_valid_lei
from brdo.vocab import (
    ActionKind,
    Agreement,
    AiTrainingSignal,
    Comparator,
    Confidence,
    CovenantCategory,
    CovenantSpecificity,
    DateBasis,
    DiscrepancyKind,
    DiscrepancyStatus,
    DocumentDateKind,
    DocumentRole,
    DocumentType,
    ExcerptPolicy,
    InstrumentProperty,
    LinkBasis,
    NoticeKind,
    ProvisionLinkBasis,
    Recipient,
    RedistributionPolicy,
    RetrievalPolicy,
    SearchChannel,
    SearchOutcome,
    SearchPurpose,
    SourceKind,
    TestBasis,
    TestFrequency,
    ThresholdUnit,
)

MAX_QUOTE_CHARS = 800
"""Upper bound on any verbatim excerpt; sources whose terms restrict reuse set a lower ``quote_limit``."""

MIN_ANCHOR_CHARS = 3
"""Shorter cells such as "NA" occur everywhere on a page, so matching them proves nothing."""


def _check_isin(value: str) -> str:
    if not is_valid_isin(value):
        raise ValueError(f"invalid ISIN (format or check digit): {value}")
    return value


def _check_cin(value: str) -> str:
    if not is_valid_cin(value):
        raise ValueError(f"invalid CIN: {value}")
    return value


def _check_lei(value: str) -> str:
    if not is_valid_lei(value):
        raise ValueError(f"invalid LEI: {value}")
    return value


RecordId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]*$", max_length=120)]
Isin = Annotated[str, AfterValidator(_check_isin)]
Cin = Annotated[str, AfterValidator(_check_cin)]
Lei = Annotated[str, AfterValidator(_check_lei)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Quote = Annotated[str, Field(min_length=3, max_length=MAX_QUOTE_CHARS)]
ReportedText = Annotated[str, Field(max_length=MAX_QUOTE_CHARS)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Evidence(Record):
    """A verifiable pointer into a document the pipeline has retrieved and hashed."""

    document: RecordId
    page: int | None = Field(default=None, ge=1, description="1-based page of the file, not the printed folio")
    quote: Quote | None = None
    locator: str | None = Field(default=None, description='Human-readable position, e.g. "Table 5, Sr. No. 4"')
    visual_fallback: bool = Field(
        default=False,
        description="The words are visible on the rendered page but may be absent from the file's text layer",
    )


class Observation(Record):
    """A value seen on a page the project may cite but not store.

    Used for link-only sources such as depository databases whose terms forbid
    storing their content. Observations cannot be re-verified automatically.
    """

    url: str
    observed_on: date
    value_seen: Annotated[str, Field(max_length=300)]
    note: str | None = None


class Period(Record):
    start: date
    end: date

    @model_validator(mode="after")
    def _ordered(self) -> "Period":
        if self.start > self.end:
            raise ValueError(f"period starts after it ends: {self.start} > {self.end}")
        return self


class TermsReview(Record):
    reviewed_on: date
    urls: list[str]
    summary: str


class Source(Record):
    """A publisher, together with the project's access and reuse policy for it."""

    id: RecordId
    name: str
    kind: SourceKind
    domains: list[str] = Field(default_factory=list)
    retrieval: RetrievalPolicy
    redistribution: RedistributionPolicy
    excerpts: ExcerptPolicy
    quote_limit: int = Field(
        default=MAX_QUOTE_CHARS,
        ge=0,
        le=MAX_QUOTE_CHARS,
        description="Longest quotation of this source outside contract clauses",
    )
    ai_training: AiTrainingSignal = AiTrainingSignal.UNSPECIFIED
    sebi_registration: str | None = None
    terms: TermsReview | None = None
    notes: str | None = None


class DocumentDate(Record):
    kind: DocumentDateKind
    value: date
    basis: DateBasis


class Document(Record):
    """One specific file. A revised file at the same address is a new document."""

    id: RecordId
    source: RecordId
    type: DocumentType
    title: str
    url: str
    landing_page: str | None = None
    retrieved_at: datetime | None = None
    retrieved_manually: bool = Field(
        default=False, description="Downloaded in a browser, outside the pipeline; see `brdo add-document --from-file`"
    )
    sha256: Sha256 | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    media_type: str | None = None
    pages: int | None = Field(default=None, ge=1)
    dates: list[DocumentDate] = Field(default_factory=list)
    period: Period | None = None
    as_of: date | None = Field(default=None, description='"Status as on" date printed in a report')
    supersedes: list[RecordId] = Field(default_factory=list)
    regulatory_basis: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _retrieval_is_hashed(self) -> "Document":
        if self.retrieved_at is not None and self.sha256 is None:
            raise ValueError(f"{self.id}: a retrieved document must record its SHA-256")
        if self.id in self.supersedes:
            raise ValueError(f"{self.id}: a document cannot supersede itself")
        return self


class NameVariant(Record):
    name: str
    evidence: list[Evidence] = Field(min_length=1)


class Issuer(Record):
    id: RecordId
    name: str
    cin: Cin | None = None
    lei: Lei | None = None
    sector: str | None = None
    name_variants: list[NameVariant] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)


class Claim(Record):
    """An attributed statement about one attribute of an instrument.

    Claims are never overwritten: if two sources disagree, both claims stay and
    a discrepancy record explains the disagreement.
    """

    property: InstrumentProperty
    value: str | float | bool | date
    asserted_by: RecordId
    evidence: list[Evidence] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    as_of: date | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _has_support(self) -> "Claim":
        if not self.evidence and not self.observations:
            raise ValueError(f"claim on {self.property} has neither evidence nor an observation")
        return self


class DocumentLink(Record):
    """Attaches a document to an instrument, stating why the link holds."""

    document: RecordId
    role: DocumentRole
    basis: LinkBasis
    confidence: Confidence
    evidence: list[Evidence] = Field(min_length=1)
    note: str | None = None


class Instrument(Record):
    isin: Isin
    issuer: RecordId
    claims: list[Claim] = Field(default_factory=list)
    documents: list[DocumentLink] = Field(default_factory=list)
    notes: str | None = None


class Threshold(Record):
    comparator: Comparator
    value: float
    unit: ThresholdUnit
    applies_from: date | None = None
    applies_to: date | None = None


class Provision(Record):
    """One contractual undertaking, quoted from the document that creates it.

    ``text`` is verbatim. ``category``, ``metric``, ``thresholds`` and
    ``explanation`` are project annotations and are only filled where the text
    makes them unambiguous.
    """

    id: RecordId
    document: RecordId
    clause: str = Field(description="Clause number exactly as printed, e.g. 6.2.2(a)(iii)")
    heading: str | None = Field(default=None, description="Document heading the clause sits under, verbatim")
    page: int = Field(ge=1)
    text: Quote
    instruments: list[Isin] = Field(min_length=1)
    category: CovenantCategory
    metric: str | None = None
    thresholds: list[Threshold] = Field(default_factory=list)
    test_frequency: TestFrequency | None = None
    test_basis: list[TestBasis] = Field(default_factory=list)
    explanation: str | None = Field(default=None, description="Plain-English annotation; not legal advice")
    annotation_reviewed: bool = False
    amends: RecordId | None = None
    effective_from: date | None = None
    visual_fallback: bool = Field(
        default=False, description="Read from the rendered page; the text layer is unreliable"
    )
    notes: str | None = None

    @model_validator(mode="after")
    def _thresholds_need_metric(self) -> "Provision":
        if self.thresholds and not self.metric:
            raise ValueError(f"{self.id}: thresholds are recorded without naming the metric they apply to")
        return self

    def anchor(self) -> Evidence:
        return Evidence(document=self.document, page=self.page, quote=self.text, visual_fallback=self.visual_fallback)


class ReportedDate(Record):
    """A date exactly as printed, with the project's reading of it."""

    raw: str
    value: date | None = None
    note: str | None = Field(default=None, description="Required when the value is not a direct parse of raw")

    @model_validator(mode="after")
    def _value_matches_raw(self) -> "ReportedDate":
        parsed = parse_printed_date(self.raw)
        if parsed is not None and self.value is not None and parsed != self.value:
            raise ValueError(f"printed date {self.raw!r} reads as {parsed}, but value is {self.value}")
        if parsed is None and self.value is not None and not self.note:
            raise ValueError(f"value {self.value} for unparseable printed date {self.raw!r} needs a note")
        return self


class Intimation(Record):
    recipients: list[Recipient] = Field(min_length=1)
    dated: date


class ReportedAction(Record):
    kind: ActionKind
    dated: date | None = None


class ProvisionLink(Record):
    """Connects a reported breach to the contract clause it concerns (project analysis)."""

    provision: RecordId
    basis: ProvisionLinkBasis
    agreement: Agreement
    note: str | None = None


class BreachItem(Record):
    """One covenant cell of a breach report row, with the ISINs printed beside it."""

    isins: list[Isin] = Field(min_length=1)
    covenant_as_reported: Quote
    page: int = Field(ge=1)
    truncated: bool = Field(default=False, description="The cell continues in the source beyond this quotation")
    levels_stated: list[str] = Field(
        default_factory=list, description="Every percentage, multiple and crore amount printed in the whole cell"
    )
    clause_reference_as_reported: str | None = None
    category: CovenantCategory
    specificity: CovenantSpecificity
    assignment_uncertain: bool = Field(
        default=False, description="Which issuer or row these ISINs belong to depends on reading merged table cells"
    )
    provisions: list[ProvisionLink] = Field(default_factory=list)

    def anchor(self, document: str) -> Evidence:
        return Evidence(document=document, page=self.page, quote=self.covenant_as_reported)


class BreachRow(Record):
    """One row of a debenture trustee's covenant breach status report (Annex-VIIA Table 5)."""

    row: str = Field(description="Serial number as printed; one printed row may be split where its cells differ")
    page: int = Field(ge=1, description="Page on which this row's dates and action cells are printed")
    issuer_name_as_reported: ReportedText | None = Field(default=None, description="None when no name is printed")
    issuer: RecordId
    items: list[BreachItem] = Field(min_length=1)
    security_enforcement_as_reported: ReportedText | None = None
    actual_breach: ReportedDate | None = None
    detected: ReportedDate | None = None
    intimation_as_reported: ReportedText | None = None
    intimations: list[Intimation] = Field(default_factory=list)
    delay_in_detection_as_reported: ReportedText | None = None
    delay_in_intimation_as_reported: ReportedText | None = None
    delay_reasons_as_reported: ReportedText | None = None
    further_action_as_reported: ReportedText | None = None
    truncated_fields: list[str] = Field(
        default_factory=list, description="Fields whose cells continue in the source beyond the quotation"
    )
    other_columns_as_reported: dict[str, ReportedText] = Field(
        default_factory=dict, description="Columns the trustee prints beyond the prescribed format, keyed by heading"
    )
    actions: list[ReportedAction] = Field(default_factory=list, description="Project reading of the action cells")
    transcribed_from_rendering: bool = Field(
        default=False,
        description="Some cells of this row are absent from the file's text layer and were read from the rendered page",
    )
    carried_over_from: date | None = Field(
        default=None, description="End of the earlier quarter this row's own label assigns the breach to"
    )
    evidence: list[Evidence] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _intimation_dates_are_printed(self) -> "BreachRow":
        quoted = " ".join(item.quote or "" for item in self.evidence)
        printed = find_printed_dates(
            f"{self.intimation_as_reported or ''} {self.further_action_as_reported or ''} {quoted}"
        )
        missing = [intimation.dated for intimation in self.intimations if intimation.dated not in printed]
        if missing:
            raise ValueError(f"row {self.row}: intimation dates {missing} are not printed in the row")
        return self

    @property
    def isins(self) -> list[str]:
        return sorted({isin for item in self.items for isin in item.isins})

    def anchors(self, document: str) -> Iterator[Evidence]:
        """Everything this row says the report printed, as checkable anchors."""
        fallback = self.transcribed_from_rendering

        def anchor(text: str, page: int | None) -> Evidence:
            return Evidence(document=document, page=page, quote=text, visual_fallback=fallback)

        for item in self.items:
            yield anchor(item.covenant_as_reported, item.page)
            for level in item.levels_stated:
                if len(level) >= MIN_ANCHOR_CHARS:
                    yield anchor(level, item.page)
            for isin in item.isins:
                yield anchor(isin, None)
        printed = [
            self.issuer_name_as_reported,
            self.security_enforcement_as_reported,
            self.actual_breach.raw if self.actual_breach else None,
            self.detected.raw if self.detected else None,
            self.intimation_as_reported,
            self.delay_reasons_as_reported,
            self.further_action_as_reported,
            *self.other_columns_as_reported.values(),
        ]
        for text in printed:
            if text and len(text) >= MIN_ANCHOR_CHARS:
                yield anchor(text, self.page)
        yield from self.evidence


class PrintedNote(Record):
    """A note or footnote printed in a report, such as a definition of what a date column means."""

    page: int = Field(ge=1)
    text: Quote


class NoInformationEntry(Record):
    """An issuer the reporting trustee says it has received no information about."""

    issuer_name_as_reported: str
    issuer: RecordId | None = None
    page: int = Field(ge=1)


class BreachReport(Record):
    """The structured content of one covenant breach status report."""

    document: RecordId
    trustee: RecordId
    period: Period
    extraction_complete: bool = Field(
        description="True only if every row of the report has been transcribed; required before absence can be inferred"
    )
    visually_reviewed: bool = Field(
        default=False,
        description="The transcription was compared with the rendered pages; text layers can silently omit content",
    )
    nil_report: bool = False
    rows: list[BreachRow] = Field(default_factory=list)
    no_information: list[NoInformationEntry] = Field(default_factory=list)
    printed_notes: list[PrintedNote] = Field(default_factory=list)
    notes: str | None = Field(default=None, description="Project remarks about the report as a whole")

    @model_validator(mode="after")
    def _rows_or_nil(self) -> "BreachReport":
        if self.extraction_complete and not self.visually_reviewed:
            raise ValueError(f"{self.document}: a report cannot be complete without review of its rendered pages")
        if self.nil_report and self.rows:
            raise ValueError(f"{self.document}: a nil report cannot list breach rows")
        if not self.nil_report and not self.rows and not self.no_information:
            raise ValueError(f"{self.document}: report has no rows; mark it nil_report if it says so")
        return self


class BreachNotice(Record):
    """A debenture trustee's published letter to the holders of one instrument about a breach.

    Notices tie an ISIN to the trust deeds that govern it and to the clause
    concerned, which often makes them the most specific public statement of the
    contractual position when the deed itself cannot be retrieved.
    """

    id: RecordId
    document: RecordId
    page: int = Field(ge=1)
    trustee: RecordId
    kind: NoticeKind = NoticeKind.BREACH
    isins: list[Isin] = Field(min_length=1)
    isins_printed: bool = Field(
        default=True, description="False when the notice prints no ISIN and the link comes from elsewhere, see notes"
    )
    issued_on: date
    period_end: date | None = Field(default=None, description="Quarter-end the certificate relates to, where stated")
    deed_dates: list[date] = Field(default_factory=list, description="Dates of the trust deeds the notice cites")
    deed_as_reported: Quote | None = None
    issuer_intimation: date | None = Field(default=None, description="When the trustee says the issuer informed it")
    issuer_intimation_as_reported: Quote | None = None
    meeting_proposed_for: date | None = None
    clause_reference_as_reported: str | None = None
    covenant_as_reported: Quote | None = None
    covenant_page: int | None = Field(default=None, ge=1, description="Set when the covenant is on another page")
    covenant_truncated: bool = Field(default=False, description="The passage continues beyond this quotation")
    levels_stated: list[str] = Field(
        default_factory=list, description="Every percentage, multiple and crore amount printed in the whole passage"
    )
    levels_complete: bool = Field(
        default=True, description="False when part of the passage was not read, so levels_stated may be partial"
    )
    adjourned_for_lack_of_quorum: bool = False
    visual_fallback: bool = Field(default=False, description="Read from the rendered page; the file has no text layer")
    notes: str | None = None

    @model_validator(mode="after")
    def _dates_are_printed_in_their_quotes(self) -> "BreachNotice":
        if self.deed_as_reported is not None and set(self.deed_dates) != find_printed_dates(self.deed_as_reported):
            raise ValueError(f"{self.id}: deed_dates do not match the dates printed in deed_as_reported")
        quoted = self.issuer_intimation_as_reported
        if quoted is not None and self.issuer_intimation not in find_printed_dates(quoted):
            raise ValueError(f"{self.id}: issuer_intimation is not printed in issuer_intimation_as_reported")
        return self

    def anchors(self) -> Iterator[Evidence]:
        def anchor(text: str, page: int | None) -> Evidence:
            return Evidence(document=self.document, page=page, quote=text, visual_fallback=self.visual_fallback)

        if self.isins_printed:
            for isin in self.isins:
                yield anchor(isin, None)
        for text in (self.deed_as_reported, self.issuer_intimation_as_reported):
            if text:
                yield anchor(text, self.page)
        if self.covenant_as_reported:
            yield anchor(self.covenant_as_reported, self.covenant_page or self.page)
        for level in self.levels_stated:
            if len(level) >= MIN_ANCHOR_CHARS:
                yield anchor(level, self.covenant_page or self.page)


class ComplianceStatement(Record):
    """An explicit statement, for stated instruments and a stated period, about covenant compliance."""

    id: RecordId
    instruments: list[Isin] = Field(min_length=1)
    period: Period
    stated_by: RecordId
    breach_stated: bool
    evidence: list[Evidence] = Field(min_length=1)
    note: str | None = None


class RegulatoryReference(Record):
    """A passage of a regulation or circular that the project's design relies on."""

    id: RecordId
    document: RecordId
    page: int = Field(ge=1)
    quote: Quote
    relevance: str

    def anchor(self) -> Evidence:
        return Evidence(document=self.document, page=self.page, quote=self.quote)


class SearchRecord(Record):
    """One documented attempt to find something, whether or not it succeeded."""

    id: RecordId
    performed_on: date
    subject: str = Field(description="ISIN, issuer id or source id the search was about")
    purpose: SearchPurpose
    channel: SearchChannel
    query: str | None = None
    scope: list[str] = Field(default_factory=list)
    period: Period | None = Field(default=None, description="Reporting period sought, for trustee report searches")
    outcome: SearchOutcome
    documents: list[RecordId] = Field(default_factory=list)
    urls_seen: list[str] = Field(default_factory=list, description="Candidates seen but not retrieved")
    note: str | None = None

    @model_validator(mode="after")
    def _found_means_documents(self) -> "SearchRecord":
        if self.outcome is SearchOutcome.FOUND and not self.documents:
            raise ValueError(f"{self.id}: a successful search must name the documents it found")
        return self


class Discrepancy(Record):
    id: RecordId
    kind: DiscrepancyKind
    subject: str
    description: str
    evidence: list[Evidence] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    status: DiscrepancyStatus = DiscrepancyStatus.OPEN
    resolution: str | None = None

    @model_validator(mode="after")
    def _resolution_documented(self) -> "Discrepancy":
        if self.status is DiscrepancyStatus.RESOLVED and not self.resolution:
            raise ValueError(f"{self.id}: a resolved discrepancy must say how it was resolved")
        return self
