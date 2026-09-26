from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


QUESTION_TYPES = ("summary", "authors", "date", "categories")
TEST_SET_SIZE = 10


def build_test_set(df: pd.DataFrame, output_path: str | Path) -> list[dict[str, Any]]:
    """Create ten reproducible questions spanning publication dates and four tasks.

    Use ten distinct papers from the clean baseline. Keep the saved test set
    unchanged when evaluating corrupted or repaired data for a fair comparison.
    Summary questions target the first sentence, matching the extractive QA task.
    """
    required = (
        "paper_id", "title", "summary", "authors_joined", "published", "categories_joined"
    )
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing test-set columns: {', '.join(sorted(missing))}")
    papers = df.loc[:, list(required)].copy()
    for column in required:
        if papers[column].isna().any() or papers[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"Test-set column {column!r} must contain nonempty values.")
        papers[column] = papers[column].astype(str)
    if papers["paper_id"].duplicated().any():
        raise ValueError("Test set requires unique paper_id values from the clean baseline.")
    if len(papers) < TEST_SET_SIZE:
        raise ValueError(f"At least {TEST_SET_SIZE} distinct papers are required.")
    dates = pd.to_datetime(papers["published"], errors="coerce", utc=True)
    if dates.isna().any():
        raise ValueError("Test-set published dates must be valid.")
    papers = papers.assign(_date=dates).sort_values(["_date", "paper_id"]).reset_index(drop=True)

    templates = {
        "summary": "What is the first sentence of the summary of '{title}'?",
        "authors": "Who authored '{title}'?",
        "date": "When was '{title}' published?",
        "categories": "What categories are assigned to '{title}'?",
    }
    questions: list[dict[str, Any]] = []
    for index in range(TEST_SET_SIZE):
        # Include both ends of the date range without relying on input row order.
        paper = papers.iloc[index * (len(papers) - 1) // (TEST_SET_SIZE - 1)]
        question_type = QUESTION_TYPES[index % len(QUESTION_TYPES)]
        answers = {
            "summary": first_sentence(paper["summary"]),
            "authors": paper["authors_joined"],
            "date": paper["published"],
            "categories": paper["categories_joined"],
        }
        questions.append(
            {
                "id": f"q{index + 1:02d}",
                "question_type": question_type,
                "question": templates[question_type].format(title=paper["title"]),
                "ground_truth": answers[question_type],
                "ground_truth_doc_ids": [paper["paper_id"]],
            }
        )
    write_json(Path(output_path), questions)
    return questions
