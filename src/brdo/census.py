"""Measurements of a trustee's census of monitored issues that anyone holding the same file can reproduce.

The census itself is not republished. The dataset keeps the file's hash, the count of ISINs it prints, a sample
drawn by a fixed rule, and the few rows the analysis cites.
"""

import hashlib
import re
from collections.abc import Iterable

from brdo.identifiers import is_valid_isin, printed_isins
from brdo.models import MonitoringCensus
from brdo.status import current_versions
from brdo.store import Dataset

SAMPLE_SIZE = 20
_NOT_RECEIVED = re.compile(r"\b(IN[A-Z0-9]{10}) [\d,]+\.\d{2} (?:Secured|Unsecured|UnSecured) No\b")


def marked_not_received(pages: list[str]) -> frozenset[str]:
    """ISINs in a row giving an issue size, a security flag and then "No" for the compliance report's receipt."""
    text = re.sub(r"\s+", " ", " ".join(pages))
    return frozenset(isin for isin in _NOT_RECEIVED.findall(text) if is_valid_isin(isin))


def draw_sample(population: Iterable[str], exclude: Iterable[str], size: int, seed: str) -> list[str]:
    """The ``size`` ISINs, outside ``exclude``, whose SHA-256 of ``seed:ISIN`` sorts first."""
    candidates = set(population) - set(exclude)
    ranked = sorted(candidates, key=lambda isin: hashlib.sha256(f"{seed}:{isin}".encode()).hexdigest())
    return sorted(ranked[:size])


def listed_in_breach_reports(dataset: Dataset, census: MonitoringCensus) -> set[str]:
    """ISINs the census trustee's current breach reports for the same period list."""
    reports = [
        report
        for report in dataset.breach_reports.values()
        if report.trustee == census.trustee and report.period.end == census.period.end
    ]
    return {isin for report in current_versions(reports, dataset) for row in report.rows for isin in row.isins}


def check_census(dataset: Dataset, census: MonitoringCensus, pages: list[str]) -> list[str]:
    """Differences between what the census record says and what the file itself yields."""
    printed = printed_isins(" ".join(pages))
    problems = []
    if len(printed) != census.isins_printed:
        problems.append(f"the file prints {len(printed)} valid ISINs, the record says {census.isins_printed}")
    listed = listed_in_breach_reports(dataset, census)
    if sorted(listed - printed) != sorted(census.listed_not_printed):
        problems.append(f"listed ISINs the file omits are {sorted(listed - printed)}, the record says otherwise")
    not_received = sorted(marked_not_received(pages))
    if not_received != sorted(census.report_not_received):
        problems.append(
            f"the file marks {len(not_received)} ISINs' reports as not received, the record lists otherwise"
        )
    seed = dataset.documents[census.document].sha256 or ""
    expected = draw_sample(printed, listed, len(census.sample), seed)
    if expected != sorted(census.sample):
        problems.append(f"the sample drawn from the file is {expected}, the record lists {sorted(census.sample)}")
    return problems
