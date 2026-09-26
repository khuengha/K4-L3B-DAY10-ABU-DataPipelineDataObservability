from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from core.utils import write_json


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    """Rebuild text_for_embedding strictly adhering to cleaning.py template."""
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Published: {row['published']}\n"
        f"Summary: {row['summary']}"
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: str | Path) -> pd.DataFrame:
    """Simulate 6 synthetic data corruption scenarios deterministically.

    Corruption types:
    1. Drop latest records (20% newest papers dropped).
    2. Blank summary (clear summary in select rows).
    3. Inject noise (insert gibberish text into summary).
    4. Truncate title (truncate title to < 8 characters).
    5. Stale date (shift published date back by 365 days).
    6. Duplicate rows (duplicate select rows).

    Rebuilds `text_for_embedding` and updates derived fields (`summary_chars`, `age_days`).
    Writes structured JSON log to `output_log_path`.
    """
    if df.empty:
        raise ValueError("Input DataFrame for corruption is empty.")

    # Sort deterministically by published date descending and paper_id descending
    corrupted_df = df.copy()
    corrupted_df = corrupted_df.sort_values(
        by=["published", "paper_id"], ascending=[False, False]
    ).reset_index(drop=True)

    before_count = len(corrupted_df)

    # 1. Drop latest records (20%)
    drop_count = int(before_count * 0.20)
    dropped_rows = corrupted_df.iloc[:drop_count].copy()
    dropped_ids = dropped_rows["paper_id"].tolist()
    dropped_details = [
        {"paper_id": str(row["paper_id"]), "title": str(row["title"]), "published": str(row["published"])}
        for _, row in dropped_rows.iterrows()
    ]
    corrupted_df = corrupted_df.iloc[drop_count:].reset_index(drop=True)

    # 2. Blank summary (indices 2, 6)
    blank_summary_indices = [idx for idx in [2, 6] if idx < len(corrupted_df)]
    blank_summary_ids = []
    blank_summary_details = []
    for idx in blank_summary_indices:
        paper_id = str(corrupted_df.at[idx, "paper_id"])
        old_summary = str(corrupted_df.at[idx, "summary"])
        corrupted_df.at[idx, "summary"] = ""
        corrupted_df.at[idx, "summary_chars"] = 0
        corrupted_df.at[idx, "text_for_embedding"] = _rebuild_text_for_embedding(corrupted_df.iloc[idx])
        blank_summary_ids.append(paper_id)
        blank_summary_details.append({"paper_id": paper_id, "old_summary_chars": len(old_summary)})

    # 3. Inject noise into summary (indices 3, 8)
    noise_string = " [CORRUPTED_NOISE_TEXT_XYZ_999]"
    inject_noise_indices = [idx for idx in [3, 8] if idx < len(corrupted_df)]
    inject_noise_ids = []
    inject_noise_details = []
    for idx in inject_noise_indices:
        paper_id = str(corrupted_df.at[idx, "paper_id"])
        old_summary = str(corrupted_df.at[idx, "summary"])
        new_summary = old_summary + noise_string
        corrupted_df.at[idx, "summary"] = new_summary
        corrupted_df.at[idx, "summary_chars"] = len(new_summary)
        corrupted_df.at[idx, "text_for_embedding"] = _rebuild_text_for_embedding(corrupted_df.iloc[idx])
        inject_noise_ids.append(paper_id)
        inject_noise_details.append({"paper_id": paper_id, "noise_injected": noise_string})

    # 4. Truncate title < 8 chars (indices 1, 5) -> set to 5 chars
    truncate_title_indices = [idx for idx in [1, 5] if idx < len(corrupted_df)]
    truncate_title_ids = []
    truncate_title_details = []
    for idx in truncate_title_indices:
        paper_id = str(corrupted_df.at[idx, "paper_id"])
        old_title = str(corrupted_df.at[idx, "title"])
        new_title = old_title[:5]
        corrupted_df.at[idx, "title"] = new_title
        corrupted_df.at[idx, "text_for_embedding"] = _rebuild_text_for_embedding(corrupted_df.iloc[idx])
        truncate_title_ids.append(paper_id)
        truncate_title_details.append({"paper_id": paper_id, "old_title": old_title, "truncated_title": new_title})

    # 5. Stale date: shift published date -365 days (indices 0, 4, 7, 9, 11, 13, 15)
    stale_date_indices = [idx for idx in [0, 4, 7, 9, 11, 13, 15] if idx < len(corrupted_df)]
    stale_date_ids = []
    stale_date_details = []
    for idx in stale_date_indices:
        paper_id = str(corrupted_df.at[idx, "paper_id"])
        old_pub_str = str(corrupted_df.at[idx, "published"])
        old_age = int(corrupted_df.at[idx, "age_days"])
        dt = datetime.strptime(old_pub_str, "%Y-%m-%d")
        new_dt = dt - timedelta(days=365)
        new_pub_str = new_dt.strftime("%Y-%m-%d")
        new_age = old_age + 365
        corrupted_df.at[idx, "published"] = new_pub_str
        corrupted_df.at[idx, "age_days"] = new_age
        corrupted_df.at[idx, "text_for_embedding"] = _rebuild_text_for_embedding(corrupted_df.iloc[idx])
        stale_date_ids.append(paper_id)
        stale_date_details.append({
            "paper_id": paper_id,
            "old_published": old_pub_str,
            "new_published": new_pub_str,
            "old_age_days": old_age,
            "new_age_days": new_age,
        })

    # 6. Duplicate rows (indices 0, 4)
    duplicate_indices = [idx for idx in [0, 4] if idx < len(corrupted_df)]
    duplicate_rows = corrupted_df.iloc[duplicate_indices].copy()
    duplicate_ids = duplicate_rows["paper_id"].astype(str).tolist()
    duplicate_details = [{"paper_id": pid} for pid in duplicate_ids]
    corrupted_df = pd.concat([corrupted_df, duplicate_rows], ignore_index=True)

    after_count = len(corrupted_df)

    # Build structured audit log
    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_records_before": before_count,
        "total_records_after": after_count,
        "corruption_summary": {
            "drop_latest_records": len(dropped_ids),
            "blank_summary": len(blank_summary_ids),
            "inject_noise": len(inject_noise_ids),
            "truncate_title": len(truncate_title_ids),
            "stale_date": len(stale_date_ids),
            "duplicate_rows": len(duplicate_ids),
        },
        "corruptions_applied": [
            {
                "type": "drop_latest_records",
                "drop_ratio": 0.20,
                "dropped_count": len(dropped_ids),
                "affected_paper_ids": dropped_ids,
                "details": dropped_details,
            },
            {
                "type": "blank_summary",
                "affected_paper_ids": blank_summary_ids,
                "details": blank_summary_details,
            },
            {
                "type": "inject_noise",
                "noise_string": noise_string,
                "affected_paper_ids": inject_noise_ids,
                "details": inject_noise_details,
            },
            {
                "type": "truncate_title",
                "max_chars": 5,
                "affected_paper_ids": truncate_title_ids,
                "details": truncate_title_details,
            },
            {
                "type": "stale_date",
                "shift_days": -365,
                "affected_paper_ids": stale_date_ids,
                "details": stale_date_details,
            },
            {
                "type": "duplicate_rows",
                "duplicate_count": len(duplicate_ids),
                "affected_paper_ids": duplicate_ids,
                "details": duplicate_details,
            },
        ],
    }

    write_json(Path(output_log_path), log_payload)
    return corrupted_df

