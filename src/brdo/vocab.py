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


CONTRACT_DOCUMENT_TYPES = frozenset(
    {
        DocumentType.DEBENTURE_TRUST_DEED,
        DocumentType.SUPPLEMENTAL_TRUST_DEED,
        DocumentType.GENERAL_INFORMATION_DOCUMENT,
        DocumentType.KEY_INFORMATION_DOCUMENT,
        DocumentType.PLACEMENT_MEMORANDUM,
    }
)


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
    """When the document was made publicly available."""


class DateBasis(StrEnum):
    """How a document date was established."""

    STATED_IN_DOCUMENT = "stated_in_document"
    LISTING_PAGE = "listing_page"
    HTTP_LAST_MODIFIED = "http_last_modified"
    FILE_METADATA = "file_metadata"


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


class DiscrepancyKind(StrEnum):
    IDENTITY = "identity"
    """Sources disagree about who or what an entity is (for example the trustee of an ISIN)."""
    VALUE = "value"
    NAMING = "naming"
    VERSION_CHANGE = "version_change"
    """A later version of the same disclosure differs from an earlier one."""
    LAYOUT = "layout"
    """A disclosure's layout makes an assignment (for example ISIN to issuer) uncertain."""


class DiscrepancyStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
