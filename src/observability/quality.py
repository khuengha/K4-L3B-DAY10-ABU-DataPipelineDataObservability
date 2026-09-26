from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import write_json


MAX_STALE_RATIO = 0.25


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Validate a batch with GX 1.x and save its suite and validation report.

    Expect the configured batch size, titles of at least 8 characters, and
    nonempty summaries. Freshness is reported separately from GX success.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name="papers_quality")
    expectations = [
        gx.expectations.ExpectTableRowCountToBeBetween(
            min_value=settings.max_results, max_value=settings.max_results
        ),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="summary"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=1),
    ]
    for expectation in expectations:
        suite.add_expectation(expectation)
    context.suites.add(suite)

    result = batch.validate(suite).to_json_dict()
    result["freshness"] = build_freshness_report(
        df, settings, settings.paths.quality_dir / f"{report_name}_freshness_report.json"
    )
    write_json(settings.paths.gx_dir / f"{report_name}_suite.json", suite.to_json_dict())
    write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", result)
    return result


def build_freshness_report(
    df: pd.DataFrame, settings: Settings, report_path: str | Path
) -> dict[str, Any]:
    """Report the strict age threshold and allow at most 25% stale rows.

    Empty batches and missing/invalid ages or dates cannot establish freshness.
    """
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    invalid_age = ages.isna() | ages.lt(0) | ages.isin([float("inf"), float("-inf")])
    stale_rows = int(ages.gt(settings.freshness_threshold_days).sum())
    total_rows = len(df)
    stale_ratio = stale_rows / total_rows if total_rows else 0.0
    latest = published.max()
    oldest = published.min()
    report = {
        "latest_published": latest.date().isoformat() if pd.notna(latest) else None,
        "oldest_published": oldest.date().isoformat() if pd.notna(oldest) else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": MAX_STALE_RATIO,
        "invalid_age_rows": int(invalid_age.sum()),
        "invalid_published_rows": int(published.isna().sum()),
        "is_fresh": bool(
            total_rows
            and not invalid_age.any()
            and published.notna().all()
            and stale_ratio <= MAX_STALE_RATIO
        ),
    }
    write_json(Path(report_path), report)
    return report
