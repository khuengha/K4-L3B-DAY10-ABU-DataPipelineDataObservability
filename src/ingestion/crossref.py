from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, safe_slug, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """TODO(student): parse Crossref payload thanh list PaperRecord."""
    items = (payload.get("message") or {}).get("items") or []
    records: list[PaperRecord] = []
    for item in items:
        doi = str(item.get("DOI") or "").strip()
        titles = item.get("title") or []
        title = normalize_whitespace(titles[0]) if titles else ""
        if not doi or not title:
            continue

        abstract_html = str(item.get("abstract") or "")
        summary = normalize_whitespace(abstract_html)

        authors = [
            compact_join([str(author.get("given") or ""), str(author.get("family") or "")], sep=" ").strip()
            for author in (item.get("author") or [])
        ]
        authors = [name for name in authors if name]

        categories = [normalize_whitespace(str(sub)) for sub in (item.get("subject") or []) if sub]
        primary_category = categories[0] if categories else ""

        published = _extract_date(item.get("published") or item.get("published-print") or item.get("published-online"))
        updated = _extract_datetime(item.get("created")) or published
        if not published:
            continue

        abs_url = str(item.get("URL") or f"https://doi.org/{doi}")

        records.append(
            PaperRecord(
                paper_id=safe_slug(doi),
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url="",
                comment=normalize_whitespace(str(item.get("comment") or "")),
            )
        )
    return records


def _extract_date(date_holder: dict | None) -> str:
    parts = ((date_holder or {}).get("date-parts") or [[]])[0]
    if not parts:
        return ""
    year, month, day = (list(parts) + [1, 1])[:3]
    return datetime(year, month, day).strftime("%Y-%m-%d")


def _extract_datetime(created: dict | None) -> str:
    stamp = (created or {}).get("date-time")
    if not stamp:
        return ""
    try:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _request_payload(settings: Settings) -> dict:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,created,URL,comment",
    }
    headers = {"User-Agent": "VinUni-K4-DataPipeline/1.0 (mailto:student@example.edu)"}
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.get("https://api.crossref.org/works", params=params, headers=headers, timeout=30)
            if response.status_code in {429, 503}:
                wait = 2 ** attempt
                print(f"Crossref API {response.status_code}, retry sau {wait}s (lan {attempt + 1}/4)")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            print(f"Crossref API loi: {exc}, retry lan {attempt + 1}/4")
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Khong tai duoc Crossref API sau cac lan retry: {last_error}")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """TODO(student): goi source API, luu raw response, parse thanh records."""
    paths = settings.paths

    if not settings.refresh_source and paths.raw_records_json.exists():
        records = load_raw_records(paths.raw_records_json)
        if records:
            print(f"Dung snapshot local: {len(records)} records tu {paths.raw_records_json}")
            return records

    try:
        payload = _request_payload(settings)
    except RuntimeError as exc:
        print(f"Fallback ve snapshot local ({exc})")
        if not paths.raw_api_response.exists():
            raise
        payload = json.loads(paths.raw_api_response.read_text(encoding="utf-8"))
    else:
        write_json(paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    if not records:
        raise RuntimeError("Crossref payload khong chua record hop le nao.")

    write_json(paths.raw_records_json, [record.__dict__ for record in records])
    print(f"Da tai va parse {len(records)} records tu Crossref API")
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """TODO(student): doc JSON snapshot va map thanh `PaperRecord`."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return parse_crossref_payload(data)
    return [_record_from_dict(item) for item in data]


def _record_from_dict(item: dict) -> PaperRecord:
    return PaperRecord(
        paper_id=str(item.get("paper_id") or ""),
        title=str(item.get("title") or ""),
        summary=str(item.get("summary") or ""),
        authors=list(item.get("authors") or []),
        categories=list(item.get("categories") or []),
        primary_category=str(item.get("primary_category") or ""),
        published=str(item.get("published") or ""),
        updated=str(item.get("updated") or ""),
        abs_url=str(item.get("abs_url") or ""),
        pdf_url=str(item.get("pdf_url") or ""),
        comment=str(item.get("comment") or ""),
    )
