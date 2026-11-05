"""Flat, deterministic exports of the dataset (CSV and SQLite).

All exports are computed by ``tables`` so that every output format carries the
same rows. Rows derived from a source that reserves AI-training rights carry
``ai_training_reserved = true`` so downstream users can exclude them.
"""

import csv
import json
import sqlite3
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from brdo.census import listed_in_breach_reports
from brdo.consistency import (
    OUTCOME_STATES,
    FollowUpState,
    PeriodAttribution,
    compare_notices_with_reports,
    compare_statements_with_reports,
    field_flows,
    follow_up_states,
    unattributed_follow_up,
)
from brdo.dictionary import datapackage
from brdo.identifiers import isin_issuer_code
from brdo.models import Evidence, Instrument
from brdo.pit import Support, as_of, availability, code_owners, shown_public_by, supports
from brdo.status import derive_all
from brdo.store import Dataset
from brdo.vocab import (
    EXECUTED_CONTRACT_TYPES,
    OFFER_DOCUMENT_TYPES,
    AiTrainingSignal,
    AvailabilityMode,
    DocumentType,
    InstrumentProperty,
    RedistributionPolicy,
    SupportBasis,
)

Row = dict[str, Any]

NO_FOLLOW_UP_PUBLISHED = "no follow-up published"


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return "; ".join(str(_cell(item)) for item in value)
    if hasattr(value, "value"):
        return value.value
    return value


def _anchors(evidence: Iterable[Evidence]) -> str:
    return "; ".join(f"{item.document}#p{item.page}" if item.page else item.document for item in evidence)


def _flow_evidence(evidence) -> str | None:
    """Every line, item or letter behind a field-level decision, as JSON, or empty when none satisfied the rule."""
    if not evidence:
        return None
    return json.dumps(
        [{"document": e.document, "page": e.page, "locator": e.locator, "matched": e.matched} for e in evidence]
    )


def _reserved(dataset: Dataset, document_id: str) -> bool:
    document = dataset.documents.get(document_id)
    if document is None:
        return False
    return dataset.sources[document.source].ai_training is AiTrainingSignal.RESERVED


def _support_dates(dataset: Dataset, support: Support, mode: AvailabilityMode) -> date | None:
    """The first day a view of ``mode`` admits the support. An observation counts from the day it was made, and
    nothing bounds it from below."""
    if support.observation is not None:
        return None if mode is AvailabilityMode.POSSIBLE else support.observation.observed_on
    day = shown_public_by(dataset.documents[support.document], dataset, mode)
    return None if day == date.min else day


def _first_established(dataset: Dataset, found: list[Support], mode: AvailabilityMode) -> date | None:
    days = [_support_dates(dataset, s, mode) for s in found if s.establishes]
    if mode is AvailabilityMode.POSSIBLE and any(day is None for day in days):
        return None  # one support has no lower bound, so the entity could have been established on any day
    return min((day for day in days if day is not None), default=None)


def _later(*days: date | None) -> date | None:
    return None if any(day is None for day in days) else max(days)  # type: ignore[type-var]


def _code_inferences(dataset: Dataset, supported: dict[tuple[str, str, str], list[Support]]) -> list[Row]:
    """Rows for issuer links inferred from an ISIN's issuer code, with the days they first hold in each view."""
    owners = code_owners(dataset)
    rows = []
    for isin, held in sorted(dataset.instruments.items()):
        code = isin_issuer_code(isin)
        if owners[code] != {held.issuer}:
            continue
        others = [
            other
            for other in sorted(dataset.instruments)
            if other != isin
            and isin_issuer_code(other) == code
            and any(s.establishes for s in supported.get(("instrument", other, "issuer"), []))
        ]
        if not others:
            continue

        def when(other: str, mode: AvailabilityMode, isin: str = isin) -> date | None:
            own = _first_established(dataset, supported.get(("instrument", isin, "identity"), []), mode)
            borrowed = _first_established(dataset, supported.get(("instrument", other, "issuer"), []), mode)
            return _later(own, borrowed)

        best = min(others, key=lambda other: (when(other, AvailabilityMode.ESTIMATED) or date.max, other))
        rows.append(
            {
                "entity": "instrument",
                "key": isin,
                "attribute": "issuer",
                "basis": SupportBasis.ISSUER_CODE,
                "establishes": True,
                "record": f"issuer code {code}, shared with {best}",
                "document": None,
                "observed_at_url": None,
                "matched_as_reported": code,
                "explanation": f"{best}'s issuer is established by a record, and no other issuer uses code {code}",
                "available_not_before": min(
                    (day for other in others if (day := when(other, AvailabilityMode.POSSIBLE))), default=None
                ),
                "available_estimate": min(
                    (day for other in others if (day := when(other, AvailabilityMode.ESTIMATED))), default=None
                ),
                "available_confirmed_by": min(
                    (day for other in others if (day := when(other, AvailabilityMode.OBSERVED))), default=None
                ),
            }
        )
    return rows


def _linked(dataset: Dataset, instrument: Instrument, types: frozenset[DocumentType]) -> list[str]:
    """The instrument's linked documents of the given types."""
    return sorted(link.document for link in instrument.documents if dataset.documents[link.document].type in types)


def tables(dataset: Dataset) -> dict[str, list[Row]]:
    out: dict[str, list[Row]] = {}
    every_support = supports(dataset)
    supported: dict[tuple[str, str, str], list[Support]] = {}
    for support in every_support:
        supported.setdefault((support.entity, support.key, support.attribute), []).append(support)

    def first(entity: str, key: str, attribute: str, mode: AvailabilityMode) -> date | None:
        return _first_established(dataset, supported.get((entity, key, attribute), []), mode)

    out["sources"] = [
        {
            "id": s.id,
            "name": s.name,
            "kind": s.kind,
            "retrieval": s.retrieval,
            "redistribution": s.redistribution,
            "excerpts": s.excerpts,
            "quote_limit": s.quote_limit,
            "domains": [] if s.redistribution is RedistributionPolicy.NO_LINKS else s.domains,
            "ai_training": s.ai_training,
            "sebi_registration": s.sebi_registration,
            "terms_reviewed_on": s.terms.reviewed_on if s.terms else None,
            "terms_summary": s.terms.summary if s.terms else None,
            "notes": s.notes,
        }
        for s in sorted(dataset.sources.values(), key=lambda s: s.id)
    ]

    def dated(document, kind: str) -> tuple[date | None, str | None]:
        for entry in document.dates:
            if entry.kind.value == kind:
                return entry.value, entry.basis.value
        return None, None

    out["documents"] = []
    for d in sorted(dataset.documents.values(), key=lambda d: d.id):
        dated_on, dated_basis = dated(d, "dated")
        signed_on, _ = dated(d, "signed")
        published_on, published_basis = dated(d, "published")
        found = availability(d, dataset)
        out["documents"].append(
            {
                "id": d.id,
                "source": d.source,
                "type": d.type,
                "title": d.title,
                "url": d.url,
                "landing_page": d.landing_page,
                "retrieved_at": d.retrieved_at,
                "retrieved_manually": d.retrieved_manually,
                "source_retrieval_policy": dataset.sources[d.source].retrieval,
                "sha256": d.sha256,
                "size_bytes": d.size_bytes,
                "media_type": d.media_type,
                "pages": d.pages,
                "dated": dated_on,
                "dated_basis": dated_basis,
                "signed": signed_on,
                "published": published_on,
                "published_basis": published_basis,
                "last_modified": found.last_modified,
                "available_not_before": found.not_before,
                "available_not_before_basis": found.not_before_basis if found.not_before else None,
                "available_estimate": found.estimate,
                "available_estimate_basis": found.estimate_basis,
                "available_confirmed_by": found.confirmed_by,
                "available_window_days": found.window_days,
                "robots_at_retrieval": d.robots_at_retrieval,
                "period_start": d.period.start if d.period else None,
                "period_end": d.period.end if d.period else None,
                "as_of": d.as_of,
                "supersedes": d.supersedes,
                "regulatory_basis": d.regulatory_basis,
                "ai_training_reserved": _reserved(dataset, d.id),
            }
        )

    out["issuers"] = [
        {
            "id": i.id,
            "name": i.name,
            "cin": i.cin,
            "lei": i.lei,
            "sector": i.sector,
            "name_variants": [variant.name for variant in i.name_variants],
            "established_not_before": first("issuer", i.id, "identity", AvailabilityMode.POSSIBLE),
            "established_estimate": first("issuer", i.id, "identity", AvailabilityMode.ESTIMATED),
            "established_confirmed_by": first("issuer", i.id, "identity", AvailabilityMode.OBSERVED),
        }
        for i in sorted(dataset.issuers.values(), key=lambda i: i.id)
    ]

    inferred = _code_inferences(dataset, supported)
    out["attribute_support"] = sorted(
        [
            {
                "entity": s.entity,
                "key": s.key,
                "attribute": s.attribute,
                "basis": s.basis,
                "establishes": s.establishes,
                "record": s.record,
                "document": s.document,
                "observed_at_url": s.observation.url if s.observation else None,
                "matched_as_reported": s.matched,
                "explanation": s.explanation,
                "available_not_before": _support_dates(dataset, s, AvailabilityMode.POSSIBLE),
                "available_estimate": _support_dates(dataset, s, AvailabilityMode.ESTIMATED),
                "available_confirmed_by": _support_dates(dataset, s, AvailabilityMode.OBSERVED),
            }
            for s in every_support
        ]
        + inferred,
        key=lambda r: (
            r["entity"],
            r["key"],
            r["attribute"],
            str(r["basis"]),
            r["record"],
            r["document"] or "",
            r["observed_at_url"] or "",
        ),
    )
    links = {row["key"]: row for row in inferred}
    latest = max(
        (day for d in dataset.documents.values() if (day := availability(d, dataset).confirmed_by)), default=None
    )
    link_basis = as_of(dataset, latest, AvailabilityMode.ESTIMATED).relationship_bases if latest is not None else {}

    def link_first(isin: str, mode: AvailabilityMode) -> date | None:
        direct = _first_established(dataset, supported.get(("instrument", isin, "issuer"), []), mode)
        code = links.get(isin, {}).get(
            {
                AvailabilityMode.POSSIBLE: "available_not_before",
                AvailabilityMode.ESTIMATED: "available_estimate",
                AvailabilityMode.OBSERVED: "available_confirmed_by",
            }[mode]
        )
        return min((day for day in (direct, code) if day is not None), default=None)

    out["instruments"], out["claims"], out["document_links"] = [], [], []
    for isin in sorted(dataset.instruments):
        instrument = dataset.instruments[isin]
        trustees = sorted(
            {str(c.value) for c in instrument.claims if c.property is InstrumentProperty.DEBENTURE_TRUSTEE}
        )
        out["instruments"].append(
            {
                "isin": isin,
                "issuer": instrument.issuer,
                "issuer_name": dataset.issuers[instrument.issuer].name,
                "trustees_claimed": trustees,
                "trustee_claims_conflict": len(trustees) > 1,
                "offer_documents": _linked(dataset, instrument, OFFER_DOCUMENT_TYPES),
                "executed_deeds": _linked(dataset, instrument, EXECUTED_CONTRACT_TYPES),
                "provisions": sum(1 for p in dataset.provisions.values() if isin in p.instruments),
                "trust_deed_dates": sorted(
                    {d for n in dataset.breach_notices.values() if isin in n.isins for d in n.deed_dates}
                ),
                "established_not_before": first("instrument", isin, "identity", AvailabilityMode.POSSIBLE),
                "established_estimate": first("instrument", isin, "identity", AvailabilityMode.ESTIMATED),
                "established_confirmed_by": first("instrument", isin, "identity", AvailabilityMode.OBSERVED),
                "issuer_link_basis": link_basis.get(isin),
                "issuer_link_estimate": link_first(isin, AvailabilityMode.ESTIMATED),
                "issuer_link_confirmed_by": link_first(isin, AvailabilityMode.OBSERVED),
                "notes": instrument.notes,
            }
        )
        for claim in instrument.claims:
            out["claims"].append(
                {
                    "isin": isin,
                    "property": claim.property,
                    "value": claim.value,
                    "asserted_by": claim.asserted_by,
                    "as_of": claim.as_of,
                    "evidence": _anchors(claim.evidence),
                    "observed_at_urls": [o.url for o in claim.observations],
                    "note": claim.note,
                }
            )
        for link in instrument.documents:
            out["document_links"].append(
                {
                    "isin": isin,
                    "document": link.document,
                    "role": link.role,
                    "basis": link.basis,
                    "confidence": link.confidence,
                    "evidence": _anchors(link.evidence),
                    "note": link.note,
                }
            )

    out["provisions"] = [
        {
            "id": p.id,
            "document": p.document,
            "document_type": dataset.documents[p.document].type,
            "clause": p.clause,
            "heading": p.heading,
            "page": p.page,
            "category": p.category,
            "metric": p.metric,
            "thresholds": json.dumps(
                [t.model_dump(mode="json", exclude_none=True) for t in p.thresholds], sort_keys=True
            )
            if p.thresholds
            else None,
            "test_frequency": p.test_frequency,
            "test_basis": [b.value for b in p.test_basis],
            "instruments": p.instruments,
            "amends": p.amends,
            "effective_from": p.effective_from,
            "stage": p.stage,
            "text": p.text,
            "explanation": p.explanation,
            "annotation_reviewed": p.annotation_reviewed,
            "ai_training_reserved": _reserved(dataset, p.document),
        }
        for p in sorted(dataset.provisions.values(), key=lambda p: p.id)
    ]

    out["breach_report_items"] = []
    for document_id in sorted(dataset.breach_reports):
        report = dataset.breach_reports[document_id]
        document = dataset.documents[document_id]
        for row in report.rows:
            first_intimation = min((i.dated for i in row.intimations), default=None)
            for item in row.items:
                for isin in item.isins:
                    out["breach_report_items"].append(
                        {
                            "report": document_id,
                            "trustee": report.trustee,
                            "period_end": report.period.end,
                            "as_of": document.as_of,
                            "supersedes": document.supersedes,
                            "row": row.row,
                            "issuer": row.issuer,
                            "issuer_name_as_reported": row.issuer_name_as_reported,
                            "isin": isin,
                            "assignment_uncertain": item.assignment_uncertain,
                            "category": item.category,
                            "specificity": item.specificity,
                            "clause_reference_as_reported": item.clause_reference_as_reported,
                            "covenant_as_reported": item.covenant_as_reported,
                            "covenant_truncated": item.truncated,
                            "levels_stated": item.levels_stated,
                            "page": item.page,
                            "actual_breach_as_reported": row.actual_breach.raw if row.actual_breach else None,
                            "actual_breach": row.actual_breach.value if row.actual_breach else None,
                            "detected_as_reported": row.detected.raw if row.detected else None,
                            "detected": row.detected.value if row.detected else None,
                            "first_intimation": first_intimation,
                            "intimation_as_reported": row.intimation_as_reported,
                            "delay_in_detection_as_reported": row.delay_in_detection_as_reported,
                            "delay_in_intimation_as_reported": row.delay_in_intimation_as_reported,
                            "delay_reasons_as_reported": row.delay_reasons_as_reported,
                            "further_action_as_reported": row.further_action_as_reported,
                            "truncated_fields": row.truncated_fields,
                            "other_columns_as_reported": json.dumps(row.other_columns_as_reported, sort_keys=True)
                            if row.other_columns_as_reported
                            else None,
                            "actions": [a.kind.value for a in row.actions],
                            "transcribed_from_rendering": row.transcribed_from_rendering,
                            "linked_provisions": [link.provision for link in item.provisions],
                            "provision_agreement": [link.agreement.value for link in item.provisions],
                            "ai_training_reserved": _reserved(dataset, document_id),
                        }
                    )

    out["no_information_entries"] = [
        {
            "report": document_id,
            "trustee": dataset.breach_reports[document_id].trustee,
            "period_end": dataset.breach_reports[document_id].period.end,
            "issuer_name_as_reported": entry.issuer_name_as_reported,
            "issuer": entry.issuer,
            "page": entry.page,
        }
        for document_id in sorted(dataset.breach_reports)
        for entry in dataset.breach_reports[document_id].no_information
    ]

    out["breach_notices"] = [
        {
            "id": n.id,
            "document": n.document,
            "page": n.page,
            "trustee": n.trustee,
            "kind": n.kind,
            "isins": n.isins,
            "isins_printed": n.isins_printed,
            "issued_on": n.issued_on,
            "period_end": n.period_end,
            "deed_dates": n.deed_dates,
            "deed_as_reported": n.deed_as_reported,
            "issuer_intimation": n.issuer_intimation,
            "meeting_proposed_for": n.meeting_proposed_for,
            "clause_reference_as_reported": n.clause_reference_as_reported,
            "covenant_as_reported": n.covenant_as_reported,
            "covenant_truncated": n.covenant_truncated,
            "levels_stated": n.levels_stated,
            "adjourned_for_lack_of_quorum": n.adjourned_for_lack_of_quorum,
            "read_from_rendering": n.visual_fallback,
            "notes": n.notes,
            "ai_training_reserved": _reserved(dataset, n.document),
        }
        for n in sorted(dataset.breach_notices.values(), key=lambda n: n.id)
    ]

    out["notice_report_comparisons"] = [
        {
            "notice": c.notice,
            "isin": c.isin,
            "report": c.report,
            "row": c.row,
            "issuer_intimation_per_notice": c.issuer_intimation,
            "detected_per_report": c.detected,
            "days_from_intimation_to_detection": c.days_from_intimation_to_detection,
            "thresholds_in_notice": sorted(c.thresholds_in_notice) if c.thresholds_in_notice is not None else None,
            "thresholds_in_report": sorted(c.thresholds_in_report),
            "thresholds_agree": c.thresholds_agree,
        }
        for c in compare_notices_with_reports(dataset)
    ]

    statements = sorted(dataset.compliance_statements.values(), key=lambda s: s.id)
    out["compliance_statements"] = [
        {
            "id": s.id,
            "document": s.document,
            "instruments": s.instruments,
            "period_start": s.period.start,
            "period_end": s.period.end,
            "stated_by": s.stated_by,
            "made_by": s.made_by,
            "scope": s.scope,
            "breach_stated": s.breach_stated,
            "isins_printed": s.isins_printed,
            "exceptions": len(s.exceptions),
            "evidence": _anchors(s.evidence),
            "note": s.note,
        }
        for s in statements
    ]

    out["compliance_statement_exceptions"] = [
        {
            "statement": s.id,
            "document": s.document,
            "page": line.page,
            "isins": line.isins,
            "covenant_as_reported": line.covenant_as_reported,
            "required_as_reported": line.required_as_reported,
            "actual_as_reported": line.actual_as_reported,
            "deed_dates_as_reported": line.deed_dates_as_reported,
            "read_from_rendering": s.visual_fallback,
        }
        for s in statements
        for line in s.exceptions
    ]

    out["statement_report_comparisons"] = [
        {
            "statement": c.statement,
            "isin": c.isin,
            "period_end": c.period_end,
            "made_by": c.made_by,
            "scope": c.scope,
            "statement_reports_breach": c.statement_reports_breach,
            "trustee_report": c.trustee_report,
            "trustee_lists": c.trustee_lists,
            "agreement": c.agreement,
            "basis": c.basis,
            "levels_only_in_statement": list(c.levels_only_in_statement),
            "statement_dated": c.statement_dated,
            "trustee_received_report": c.trustee_received_report,
            "trustee_detected": c.trustee_detected,
            "trustee_cites_certificate": c.trustee_cites_certificate,
            "trustee_could_rely_on_issuer": c.trustee_could_rely_on_issuer,
        }
        for c in compare_statements_with_reports(dataset)
    ]

    out["field_flows"] = [
        {
            "statement": f.statement,
            "isin": f.isin,
            "period_end": f.period_end,
            "trustee_report": f.trustee_report,
            "field": f.field,
            "issuer_prints": f.issuer,
            "trustee_prints": f.trustee,
            "issuer_examined": f.issuer_examined,
            "issuer_evidence": _flow_evidence(f.issuer_evidence),
            "trustee_examined": f.trustee_examined,
            "trustee_evidence": _flow_evidence(f.trustee_evidence),
            "ai_training_reserved": _reserved(dataset, dataset.compliance_statements[f.statement].document)
            or (f.trustee_report is not None and _reserved(dataset, f.trustee_report)),
        }
        for f in field_flows(dataset)
    ]

    def follow_up_row(state: FollowUpState) -> Row:
        return {
            "trustee": state.trustee,
            "isin": state.isin,
            "period_end": state.period_end,
            "state": state.state,
            "is_outcome": state.state in OUTCOME_STATES,
            "attribution": state.attribution,
            "basis": state.basis,
        }

    out["follow_up_states"] = []
    for period_end in sorted({report.period.end for report in dataset.breach_reports.values()}):
        published, listed = follow_up_states(dataset, period_end)
        with_state = {(state.trustee, state.isin) for state in published}
        rows = [follow_up_row(state) for state in published]
        rows += [
            {
                "trustee": trustee,
                "isin": isin,
                "period_end": period_end,
                "state": NO_FOLLOW_UP_PUBLISHED,
                "is_outcome": False,
                "attribution": PeriodAttribution.REPORT_ROW,
                "basis": "",
            }
            for trustee, isin in listed
            if (trustee, isin) not in with_state
        ]
        out["follow_up_states"] += sorted(rows, key=lambda r: (r["trustee"], r["isin"]))
    out["follow_up_states"] += [follow_up_row(state) for state in unattributed_follow_up(dataset)]

    out["monitoring_censuses"] = [
        {
            "id": c.id,
            "document": c.document,
            "trustee": c.trustee,
            "period_start": c.period.start,
            "period_end": c.period.end,
            "isins_printed": c.isins_printed,
            "listed_in_breach_report": len(listed_in_breach_reports(dataset, c)),
            "listed_not_printed": c.listed_not_printed,
            "sample": c.sample,
            "report_not_received": c.report_not_received,
            "rows_cited": len(c.entries),
            "ai_training_reserved": _reserved(dataset, c.document),
        }
        for c in sorted(dataset.monitoring_censuses.values(), key=lambda c: c.id)
    ]

    out["regulatory_references"] = [
        {"id": r.id, "document": r.document, "page": r.page, "quote": r.quote, "relevance": r.relevance}
        for r in sorted(dataset.regulatory_references.values(), key=lambda r: r.id)
    ]

    out["instrument_status"] = [
        {
            "isin": status.isin,
            "period_end": status.period_end,
            "status": status.status,
            "basis": status.basis,
            "documents": list(status.documents),
        }
        for status in derive_all(dataset)
    ]

    out["searches"] = [
        {
            "id": s.id,
            "performed_on": s.performed_on,
            "subject": s.subject,
            "purpose": s.purpose,
            "channel": s.channel,
            "query": s.query,
            "scope": s.scope,
            "period_end": s.period.end if s.period else None,
            "outcome": s.outcome,
            "documents": s.documents,
            "urls_seen": s.urls_seen,
            "note": s.note,
        }
        for s in sorted(dataset.searches.values(), key=lambda s: s.id)
    ]

    out["discrepancies"] = [
        {
            "id": d.id,
            "kind": d.kind,
            "subject": d.subject,
            "status": d.status,
            "description": d.description,
            "evidence": _anchors(d.evidence),
            "observed_at_urls": [o.url for o in d.observations],
            "resolution": d.resolution,
        }
        for d in sorted(dataset.discrepancies.values(), key=lambda d: d.id)
    ]

    out["evidence"] = sorted(
        (
            {
                "used_by": label,
                "document": item.document,
                "page": item.page,
                "locator": item.locator,
                "quote": item.quote,
                "read_from_rendering": item.visual_fallback,
                "ai_training_reserved": _reserved(dataset, item.document),
            }
            for label, item in dataset.evidence()
        ),
        key=lambda row: (row["document"], row["page"] or 0, row["used_by"], row["quote"] or ""),
    )
    return {name: [{key: _cell(value) for key, value in row.items()} for row in rows] for name, rows in out.items()}


def write_csv(all_tables: dict[str, list[Row]], directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name, rows in all_tables.items():
        path = directory / f"{name}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            if rows:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
        written.append(path)
    return written


def cited_sources(dataset: Dataset) -> list[dict[str, str]]:
    """The publishers of cited documents, for a data package's ``sources``, with no link for a source forbidding one."""
    found = []
    for source_id in sorted({document.source for document in dataset.documents.values()}):
        source = dataset.sources[source_id]
        entry = {"title": source.name}
        if source.redistribution is not RedistributionPolicy.NO_LINKS and source.domains:
            entry["path"] = f"https://{source.domains[0]}"
        found.append(entry)
    return found


def write_datapackage(all_tables: dict[str, list[Row]], directory: Path, dataset: Dataset) -> Path:
    """Describe the CSV files in ``directory`` as a Frictionless Data Package, column by column."""
    path = directory / "datapackage.json"
    descriptor = datapackage(all_tables, cited_sources(dataset))
    path.write_text(json.dumps(descriptor, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_sqlite(all_tables: dict[str, list[Row]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    with sqlite3.connect(path) as connection:
        for name, rows in all_tables.items():
            if not rows:
                continue
            columns = list(rows[0])
            column_sql = ", ".join(f'"{column}"' for column in columns)
            connection.execute(f'CREATE TABLE "{name}" ({column_sql})')
            placeholders = ", ".join("?" for _ in columns)
            connection.executemany(
                f'INSERT INTO "{name}" VALUES ({placeholders})',
                ([row[column] for column in columns] for row in rows),
            )
    return path
