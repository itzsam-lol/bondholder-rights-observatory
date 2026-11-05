"""Controlled vocabularies.

Every categorical field in the dataset draws its values from one of these
enumerations. Where a regulatory text already defines a taxonomy (for example
the SEBI guidance note on covenant categories), the vocabulary follows it rather
than inventing a new one.
"""

from enum import StrEnum


class SourceKind(StrEnum):
    REGULATOR = "regulator"
    EXCHANGE = "exchange"
    DEPOSITORY = "depository"
    DEBENTURE_TRUSTEE = "debenture_trustee"
    ISSUER = "issuer"
    CREDIT_RATING_AGENCY = "credit_rating_agency"
    MARKET_PORTAL = "market_portal"
    OTHER = "other"


class RetrievalPolicy(StrEnum):
    """Whether the project's pipeline may retrieve documents from a source."""

    ALLOWED = "allowed"
    MANUAL_ONLY = "manual_only"
    """The source may be consulted page by page; the pipeline must not download from it."""
    EXCLUDED = "excluded"
    """The source is not used at all, not even as a link."""


class RedistributionPolicy(StrEnum):
    OPEN = "open"
    """Documents may be redistributed (for example under an open licence)."""
    LINK_ONLY = "link_only"
    """Only links, hashes and short quotations are published, never the document."""
    NO_LINKS = "no_links"
    """Even hyperlinks require permission; the dataset carries no URL."""


class ExcerptPolicy(StrEnum):
    NONE = "none"
    SHORT_QUOTATION = "short_quotation"


class AiTrainingSignal(StrEnum):
    """Machine-readable reservation of rights published by a source."""

    UNSPECIFIED = "unspecified"
    RESERVED = "reserved"
    """The source opts out of AI training (for example ``Content-Signal: ai-train=no``)."""


class DocumentType(StrEnum):
    REGULATORY_CIRCULAR = "regulatory_circular"
    DEBENTURE_TRUST_DEED = "debenture_trust_deed"
    SUPPLEMENTAL_TRUST_DEED = "supplemental_trust_deed"
    GENERAL_INFORMATION_DOCUMENT = "general_information_document"
    KEY_INFORMATION_DOCUMENT = "key_information_document"
    PLACEMENT_MEMORANDUM = "placement_memorandum"
    """Placement memoranda and information memoranda for private placements."""
    TRUSTEE_BREACH_STATUS_REPORT = "trustee_breach_status_report"
    """SEBI Master Circular for Debenture Trustees, Annex-VIIA Table 5."""
    TRUSTEE_SECURITY_COVER_REPORT = "trustee_security_cover_report"
    """Annex-VIIA Table 3."""
    TRUSTEE_DEFAULT_STATUS_REPORT = "trustee_default_status_report"
    """Annex-VIIA Table 8."""
    TRUSTEE_PRESS_RELEASE = "trustee_press_release"
    EXCHANGE_NOTICE = "exchange_notice"
    ISSUER_FILING = "issuer_filing"
    RATING_RATIONALE = "rating_rationale"
    OTHER = "other"


EXECUTED_CONTRACT_TYPES = frozenset({DocumentType.DEBENTURE_TRUST_DEED, DocumentType.SUPPLEMENTAL_TRUST_DEED})
"""The instruments that create or amend the terms, once executed. A copy may still be a draft or unsigned."""

OFFER_DOCUMENT_TYPES = frozenset(
    {
        DocumentType.GENERAL_INFORMATION_DOCUMENT,
        DocumentType.KEY_INFORMATION_DOCUMENT,
        DocumentType.PLACEMENT_MEMORANDUM,
    }
)
"""Documents setting out the terms on which debentures were offered. They are not the executed deed."""

CONTRACT_DOCUMENT_TYPES = EXECUTED_CONTRACT_TYPES | OFFER_DOCUMENT_TYPES
"""Documents that set out the terms, at either stage. Use the two sets above wherever the stage matters."""


TERM_STATING_DOCUMENT_TYPES = CONTRACT_DOCUMENT_TYPES | {
    DocumentType.TRUSTEE_PRESS_RELEASE,
    DocumentType.TRUSTEE_BREACH_STATUS_REPORT,
    DocumentType.ISSUER_FILING,
    DocumentType.EXCHANGE_NOTICE,
    DocumentType.RATING_RATIONALE,
}
"""Documents that may quote or state a contractual term, whether or not they are the contract itself."""


class DocumentDateKind(StrEnum):
    DATED = "dated"
    """The date the document gives itself (for example "Date: June 7, 2024")."""
    SIGNED = "signed"
    PUBLISHED = "published"
    """When the publisher says the document was made publicly available, for example a date on its listing page."""
    LAST_MODIFIED = "last_modified"
    """When the server says the exact file held was last modified. It dates that version, not its first publication."""


class DateBasis(StrEnum):
    """How a document date was established."""

    STATED_IN_DOCUMENT = "stated_in_document"
    LISTING_PAGE = "listing_page"
    HTTP_LAST_MODIFIED = "http_last_modified"
    FILE_METADATA = "file_metadata"


DATE_BASES_BY_KIND = {
    DocumentDateKind.DATED: frozenset({DateBasis.STATED_IN_DOCUMENT, DateBasis.FILE_METADATA}),
    DocumentDateKind.SIGNED: frozenset({DateBasis.STATED_IN_DOCUMENT}),
    DocumentDateKind.PUBLISHED: frozenset({DateBasis.STATED_IN_DOCUMENT, DateBasis.LISTING_PAGE}),
    DocumentDateKind.LAST_MODIFIED: frozenset({DateBasis.HTTP_LAST_MODIFIED, DateBasis.FILE_METADATA}),
}
"""Which ways of knowing a date can support which meaning. A server header cannot show that a file was published."""


class AvailabilityState(StrEnum):
    """What the record shows about one exact file on one day. Only ``confirmed`` rests on the project's own evidence."""

    NOT_YET_POSSIBLE = "not_yet_possible"
    """The day precedes a lower bound: a date the file gives itself, a letter it contains or an event it records.
    If those dates are right, the file cannot have been public yet."""
    UNCERTAIN = "uncertain"
    """The file may or may not have been public: no lower bound rules it out, and the project had not yet observed
    it. A publisher's or server's date only suggests when, and is not evidence that it was."""
    CONFIRMED = "confirmed"
    """The project had retrieved this exact file from its public address by then."""


class AvailabilityMode(StrEnum):
    """Which files a point-in-time view admits on a given day. The three views nest: observed, estimated, possible."""

    OBSERVED = "observed"
    """Only files the project itself had observed by the day: what BRDO had seen, not what the public could see. No
    file counts too early, but files public long before the project looked are left out."""
    ESTIMATED = "estimated"
    """Files observed by the day, and files not yet observed that an estimate, from the publisher's or the server's
    date, puts on or before the day. A reconstruction under that stated assumption, not the public record itself."""
    POSSIBLE = "possible"
    """A retrospective upper bound, not a snapshot of what was public or known on the day: every file that no lower
    bound rules out, including files the project found much later, because the evidence cannot show they were not
    public. Nothing that could have been public is left out, but a file in it may not yet have existed publicly, and
    a file with no lower bound is let in on any day."""


class SupportBasis(StrEnum):
    """What kind of evidence supports an entity or attribute (see ``pit.supports``)."""

    QUOTED = "quoted"
    """An anchor's quotation prints the value, so ``brdo verify`` can check it against the hashed file."""
    RECOMPUTED = "recomputed"
    """The value is recomputed from the hashed file's text by ``brdo verify``, as for a census's ISIN lists."""
    OBSERVED = "observed"
    """Seen on a link-only page and recorded as an observation, which cannot be re-verified automatically."""
    FLAG_ONLY = "flag_only"
    """A curated flag says the record prints the value, but no anchor quotes it. It does not establish the value."""
    PRINTED_WITH_NAME = "printed_with_name"
    """One record prints the ISIN and the issuer's name together, such as a row of a trustee's breach report."""
    ISSUER_PUBLICATION = "issuer_publication"
    """The issuer's own website published the record, which prints the ISIN or the identifier."""
    LETTER_TO_HOLDERS = "letter_to_holders"
    """A trustee's letter to the holders of the ISIN, which the project attributes to the issuer. No transcribed
    quotation prints the issuer's name, so the attribution is the curator's reading. It does not establish the link."""
    ISSUER_CODE = "issuer_code"
    """Inferred: the ISIN's issuer code is shared with an ISIN whose issuer a record prints, and no other issuer in
    the dataset uses that code."""
    EXACT_NAME = "exact_name"
    """The printed name is the issuer's name, ignoring case, punctuation and Ltd or Pvt for Limited or Private."""
    NAME_WITH_ADDITION = "name_with_addition"
    """The printed name is the issuer's name followed by a parenthesis, such as an abbreviation or a former name."""
    NAME_VARIANT = "name_variant"
    """A recorded variant of the issuer's name is printed, with its own evidence."""


ESTABLISHING_BASES = frozenset(
    {
        SupportBasis.QUOTED,
        SupportBasis.RECOMPUTED,
        SupportBasis.OBSERVED,
        SupportBasis.PRINTED_WITH_NAME,
        SupportBasis.ISSUER_PUBLICATION,
        SupportBasis.ISSUER_CODE,
        SupportBasis.EXACT_NAME,
        SupportBasis.NAME_WITH_ADDITION,
        SupportBasis.NAME_VARIANT,
    }
)
"""Bases that establish what they support in a point-in-time view. The others are exported, labelled, but not used."""


class RobotsAtRetrieval(StrEnum):
    """What the fetcher could establish about a host's robots policy when it retrieved a file."""

    OBEYED = "obeyed"
    """A robots file was read and allowed the retrieval."""
    ABSENT = "absent"
    """The robots address answered HTTP 404 or 410: the host publishes no robots rules."""
    UNREAD = "unread"
    """No robots policy could be established, but an earlier version of the fetcher retrieved the file anyway."""


class CovenantCategory(StrEnum):
    """Covenant categories of the SEBI guidance note on covenants.

    Source: Master Circular for Debenture Trustees (28 September 2026),
    Chapter VI, Annex-VIA "Guidance note on list of Covenants". ``OTHER`` is used
    for undertakings outside that list, such as reporting obligations or
    conditions subsequent; the document's own heading is kept separately.
    """

    ACCOUNTS_FUNDS_RESERVES = "accounts_funds_reserves"
    FINANCIAL = "financial"
    AFFIRMATIVE = "affirmative"
    CREDIT_RATING = "credit_rating"
    NEGATIVE = "negative"
    DEFAULT = "default"
    OTHER = "other"


class CovenantSpecificity(StrEnum):
    """How much of the contractual term a breach report itself prints."""

    CLAUSE_TEXT = "clause_text"
    """States the undertaking in words, with any threshold."""
    REQUIREMENT_AND_ACTUAL = "requirement_and_actual"
    """Prints both the required level and the level the issuer reached."""
    CLAUSE_NUMBER_ONLY = "clause_number_only"
    DESCRIPTION_ONLY = "description_only"
    """Names or paraphrases the failure without the term, for example "Non submission of financial results"."""


class Comparator(StrEnum):
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="


class ThresholdUnit(StrEnum):
    PERCENT = "percent"
    TIMES = "times"
    INR = "inr"


class TestFrequency(StrEnum):
    CONTINUOUS = "continuous"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    ANNUAL = "annual"


class TestBasis(StrEnum):
    STANDALONE = "standalone"
    CONSOLIDATED = "consolidated"


class InstrumentProperty(StrEnum):
    DEBENTURE_TRUSTEE = "debenture_trustee"
    ALLOTMENT_DATE = "allotment_date"
    MATURITY_DATE = "maturity_date"
    COUPON_RATE = "coupon_rate"
    SECURED = "secured"
    FACE_VALUE = "face_value"
    ISSUE_SIZE = "issue_size"
    MODE_OF_ISSUE = "mode_of_issue"
    LISTING_EXCHANGE = "listing_exchange"
    SERIES = "series"
    CREDIT_RATING = "credit_rating"


class DocumentRole(StrEnum):
    """What a document is for, relative to one instrument."""

    OFFER_DOCUMENT = "offer_document"
    TRUST_DEED = "trust_deed"
    AMENDMENT = "amendment"
    LISTING = "listing"
    MONITORING = "monitoring"
    OTHER = "other"


class LinkBasis(StrEnum):
    """Why a document or statement is attached to a particular ISIN."""

    ISIN_IN_DOCUMENT = "isin_in_document"
    EXCHANGE_NOTICE = "exchange_notice"
    TRUSTEE_REPORT = "trustee_report"
    ATTRIBUTE_MATCH = "attribute_match"
    """Matched on issue size, coupon, dates or series name; the ISIN is not stated."""


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProvisionLinkBasis(StrEnum):
    """How a reported breach was connected to a contractual provision."""

    CLAUSE_REFERENCE = "clause_reference"
    TEXT_MATCH = "text_match"
    METRIC_MATCH = "metric_match"


class Agreement(StrEnum):
    """Whether a covenant as reported agrees with the contractual text."""

    CONSISTENT = "consistent"
    DIFFERS = "differs"
    NOT_COMPARABLE = "not_comparable"


class Recipient(StrEnum):
    DEBENTURE_HOLDERS = "debenture_holders"
    STOCK_EXCHANGE = "stock_exchange"
    SEBI = "sebi"
    CREDIT_RATING_AGENCY = "credit_rating_agency"
    UNSPECIFIED = "unspecified"
    """The report gives a date of intimation without saying to whom."""


class ActionKind(StrEnum):
    """Kinds of follow-up reported by a debenture trustee for a breach."""

    AWAITING_INSTRUCTIONS = "awaiting_instructions"
    FOLLOW_UP_WITH_ISSUER = "follow_up_with_issuer"
    HOLDERS_MEETING_HELD = "holders_meeting_held"
    HOLDERS_MEETING_SCHEDULED = "holders_meeting_scheduled"
    WAIVER_REPORTED = "waiver_reported"
    NO_ACTION_INSTRUCTED = "no_action_instructed"
    CURE_REPORTED = "cure_reported"
    REPORTED_AS_CONTINUING = "reported_as_continuing"
    NOMINEE_DIRECTOR = "nominee_director"
    ENFORCEMENT = "enforcement"
    OTHER = "other"


class NoticeKind(StrEnum):
    BREACH = "breach"
    MEETING_CONTINUATION = "meeting_continuation"
    """A follow-up letter, typically proposing a fresh date after a meeting was adjourned."""


class CoverageStatus(StrEnum):
    """What the reviewed public record says about breaches, for one ISIN and period.

    These categories are deliberately never merged. In particular
    ``NO_REPORT_FOUND`` means only that the reviewed sources do not list the
    instrument; it is not evidence that no breach occurred.
    """

    REPORTED_BREACH = "reported_breach"
    REPORTED_NO_BREACH = "reported_no_breach"
    NO_INFORMATION_REPORTED = "no_information_reported"
    """The reporting party states it has received no information from the issuer."""
    NO_REPORT_FOUND = "no_report_found"
    INACCESSIBLE = "inaccessible"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"
    NOT_ASSESSED = "not_assessed"


class SearchPurpose(StrEnum):
    CONTRACT_DOCUMENT = "contract_document"
    AMENDMENT = "amendment"
    TRUSTEE_REPORT = "trustee_report"
    IDENTITY = "identity"
    COMPLIANCE_STATEMENT = "compliance_statement"


class SearchChannel(StrEnum):
    WEB_SEARCH = "web_search"
    SOURCE_LISTING_PAGE = "source_listing_page"
    DIRECT_URL = "direct_url"


class SearchOutcome(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    LOCATED_NOT_RETRIEVED = "located_not_retrieved"
    """A candidate document exists at a source the pipeline may not retrieve from; it can be consulted in a browser."""
    EXCLUDED_BY_POLICY = "excluded_by_policy"
    ACCESS_ERROR = "access_error"


class ProvisionStage(StrEnum):
    """What a provision record is evidence of. Only the executed document itself establishes the operative term."""

    EXECUTED_TEXT = "executed_text"
    """Quoted from an executed debenture trust deed or supplemental deed, the instrument that creates the term."""
    OFFERED = "offered"
    """Quoted from an offer document: the terms on which the debentures were offered. The deed may differ.

    An offer document is not the executed deed, and neither shows later amendments.
    """
    DESCRIBED_IN_FORCE = "described_in_force"
    """A party's description of a term it treats as in force, such as a trustee's quotation or an issuer's level."""
    PROPOSED = "proposed"
    """A change put forward for approval, such as a proposed schedule of covenants."""
    APPROVED_IN_PRINCIPLE = "approved_in_principle"
    """A proposed change approved in principle, for example by an exchange under regulation 59, not shown executed."""


class ReviewerKind(StrEnum):
    """Who made a second annotation.

    Only a person can. There is deliberately no value for an automated process, a model, or the original curator
    re-reading their own work: none of those is an independent review.
    """

    PERSON = "person"


class ManualCheckKind(StrEnum):
    """What a manual check concerns."""

    DOCUMENT = "document"
    """A file that a person may download in a browser and ingest with ``brdo add-document --from-file``."""
    SOURCE_REVIEW = "source_review"
    """A source's pages or terms, which a person reads and records in the source's record."""


class ManualCheckStatus(StrEnum):
    """How far a manual check has gone. Nothing beyond ``not_attempted`` is set without a dated attempt."""

    NOT_ATTEMPTED = "not_attempted"
    ATTEMPTED_NOT_FOUND = "attempted_not_found"
    """A person looked, and the file or page was not there."""
    FOUND_INACCESSIBLE = "found_inaccessible"
    """The file or page exists, but a person could not open it."""
    RETRIEVED_MANUALLY = "retrieved_manually"
    """A person downloaded the file, and it is registered as a document retrieved manually."""
    INSPECTED_NOT_SUITABLE = "inspected_not_suitable"
    """A person examined it and decided, with a reason, that it should not enter the dataset."""
    INGESTED_AND_CHECKED = "ingested_and_checked"
    """The file is registered, its records are transcribed, and their anchors were verified against it."""
    RECORDED = "recorded"
    """For a source review only: what the pages or terms say is recorded in the source's record."""


class ManualCheckPriority(StrEnum):
    """The order in which the project would attempt manual checks. The reasons are in ``docs/coverage.md``."""

    FIRST = "first"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    HOLD = "hold"
    """Not to be attempted until its prerequisite is met."""


class CandidateStage(StrEnum):
    """What a candidate document would be evidence of. The legal stages are not interchangeable."""

    OFFERED = "offered"
    """An offer document: the terms on which debentures were offered, not the executed deed."""
    PROPOSED = "proposed"
    APPROVED_IN_PRINCIPLE = "approved_in_principle"
    EXECUTED = "executed"
    """An executed deed, if the copy is the signed and complete instrument."""
    NOT_A_CONTRACT_DOCUMENT = "not_a_contract_document"
    """A filing or report that may state the issuer's position, but no contract term."""
    NOT_A_DOCUMENT = "not_a_document"
    """A source's pages or terms."""


class StatementMaker(StrEnum):
    """Who made a compliance statement, which is not always who published it."""

    ISSUER = "issuer"
    STATUTORY_AUDITOR = "statutory_auditor"


class StatementScope(StrEnum):
    """Which covenants a compliance statement says it covers."""

    ALL_COVENANTS = "all_covenants"
    FINANCIAL_COVENANTS = "financial_covenants"


class DiscrepancyKind(StrEnum):
    IDENTITY = "identity"
    """Sources disagree about who or what an entity is (for example the trustee of an ISIN)."""
    VALUE = "value"
    NAMING = "naming"
    VERSION_CHANGE = "version_change"
    """A later version of the same disclosure differs from an earlier one."""
    LAYOUT = "layout"
    """A disclosure's layout makes an assignment (for example ISIN to issuer) uncertain."""
    COMPLIANCE = "compliance"
    """Statements about whether the same obligation was met disagree."""


class DiscrepancyStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
