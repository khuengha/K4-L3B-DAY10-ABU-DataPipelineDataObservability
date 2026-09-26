from __future__ import annotations

import re
from datetime import datetime, timezone

import pandas as pd

from core.utils import compact_join, normalize_whitespace, safe_slug
from ingestion.crossref import PaperRecord


def _strip_jats(text: str) -> str:
    cleaned = re.sub(r"</?jats:[^>]+>", " ", text)
    return normalize_whitespace(cleaned)


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """TODO(student): clean raw records thanh dataframe san sang de embed."""
    rows: list[dict] = []
    for record in records:
        title = normalize_whitespace(record.title)
        summary = _strip_jats(record.summary)
        if not title or not summary:
            continue

        published_dt = _parse_date(record.published)
        if published_dt is None:
            continue

        authors = [normalize_whitespace(name) for name in record.authors if name]
        categories = [normalize_whitespace(cat) for cat in record.categories if cat]
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        published_str = published_dt.strftime("%Y-%m-%d")
        age_days = max((run_date - published_dt).days, 0)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Published: {published_str}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": record.paper_id or safe_slug(record.abs_url),
                "title": title,
                "summary": summary,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "primary_category": record.primary_category,
                "published": published_str,
                "updated": record.updated,
                "age_days": age_days,
                "summary_chars": len(summary),
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.sort_values(by=["published", "paper_id"]).reset_index(drop=True)
    return df
