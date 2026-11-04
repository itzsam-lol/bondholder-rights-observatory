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

from brdo.consistency import compare_notices_with_reports
from brdo.models import Evidence
from brdo.status import derive_all
from brdo.store import Dataset
from brdo.vocab import CONTRACT_DOCUMENT_TYPES, AiTrainingSignal, InstrumentProperty

Row = dict[str, Any]


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


def _reserved(dataset: Dataset, document_id: str) -> bool:
    document = dataset.documents.get(document_id)
    if document is None:
        return False
    return dataset.sources[document.source].ai_training is AiTrainingSignal.RESERVED


def tables(dataset: Dataset) -> dict[str, list[Row]]:
    out: dict[str, list[Row]] = {}

    out["sources"] = [
        {
            "id": s.id,
            "name": s.name,
            "kind": s.kind,
            "retrieval": s.retrieval,
            "redistribution": s.redistribution,
            "excerpts": s.excerpts,
            "ai_training": s.ai_training,
            "sebi_registration": s.sebi_registration,
            "terms_reviewed_on": s.terms.reviewed_on if s.terms else None,
            "terms_summary": s.terms.summary if s.terms else None,
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
        published_on, published_basis = dated(d, "published")
        out["documents"].append(
            {
                "id": d.id,
                "source": d.source,
                "type": d.type,
                "title": d.title,
                "url": d.url,
                "landing_page": d.landing_page,
                "retrieved_at": d.retrieved_at,
                "sha256": d.sha256,
                "size_bytes": d.size_bytes,
                "media_type": d.media_type,
                "pages": d.pages,
                "dated": dated_on,
                "dated_basis": dated_basis,
                "published": published_on,
                "published_basis": published_basis,
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
        }
        for i in sorted(dataset.issuers.values(), key=lambda i: i.id)
    ]

    out["instruments"], out["claims"], out["document_links"] = [], [], []
    for isin in sorted(dataset.instruments):
        instrument = dataset.instruments[isin]
        trustees = sorted(
            {str(c.value) for c in instrument.claims if c.property is InstrumentProperty.DEBENTURE_TRUSTEE}
        )
        contract_links = [
            link for link in instrument.documents if dataset.documents[link.document].type in CONTRACT_DOCUMENT_TYPES
        ]
        out["instruments"].append(
            {
                "isin": isin,
                "issuer": instrument.issuer,
                "issuer_name": dataset.issuers[instrument.issuer].name,
                "trustees_claimed": trustees,
                "trustee_claims_conflict": len(trustees) > 1,
                "contract_documents": sorted(link.document for link in contract_links),
                "provisions": sum(1 for p in dataset.provisions.values() if isin in p.instruments),
                "trust_deed_dates": sorted(
                    {d for n in dataset.breach_notices.values() if isin in n.isins for d in n.deed_dates}
                ),
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

    out["compliance_statements"] = [
        {
            "id": s.id,
            "instruments": s.instruments,
            "period_start": s.period.start,
            "period_end": s.period.end,
            "stated_by": s.stated_by,
            "breach_stated": s.breach_stated,
            "evidence": _anchors(s.evidence),
            "note": s.note,
        }
        for s in sorted(dataset.compliance_statements.values(), key=lambda s: s.id)
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
