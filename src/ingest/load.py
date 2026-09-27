"""Load stage: fetch/parse public scheme pages into plain-text documents."""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.config import SNAPSHOTS_DIR, SOURCES_CSV
from src.ingest.export_artifacts import export_raw_documents

REQUEST_TIMEOUT_S = 45
USER_AGENT = (
    "Mozilla/5.0 (compatible; NextLeapMFBot/1.0; +https://github.com/nextleap-demo; class-demo)"
)


def load_sources(csv_path: Path | None = None) -> list[dict[str, str]]:
    """Read data/sources.csv into a list of source rows."""
    path = csv_path or SOURCES_CSV
    if not path.exists():
        raise FileNotFoundError(f"Sources CSV not found: {path}")

    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"category", "scheme_name", "url"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"sources.csv must have columns: {sorted(required)}")

        rows = [
            {
                "category": row["category"].strip(),
                "scheme_name": row["scheme_name"].strip(),
                "url": row["url"].strip(),
            }
            for row in reader
            if row.get("url", "").strip()
        ]

    if not rows:
        raise ValueError(f"No source rows found in {path}")
    return rows


def _snapshot_stem(scheme_name: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", scheme_name.lower()).strip("-")
    return stem or "scheme"


def snapshot_path(scheme_name: str, snapshots_dir: Path | None = None) -> Path:
    directory = snapshots_dir or SNAPSHOTS_DIR
    return directory / f"{_snapshot_stem(scheme_name)}.html"


def html_to_text(html: str) -> str:
    """Strip scripts/styles/chrome and return readable main text."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    for tag in soup.find_all(["nav", "header", "footer", "aside"]):
        tag.decompose()

    root = soup.find("main") or soup.find("article") or soup.body or soup
    text = root.get_text(separator="\n", strip=True)

    # Collapse excessive blank lines
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def fetch_or_read_snapshot(
    url: str,
    scheme_name: str,
    *,
    snapshots_dir: Path | None = None,
    force_fetch: bool = False,
) -> tuple[str, Path]:
    """
    Prefer an existing HTML snapshot; otherwise HTTP GET and save it.

    Returns (html, snapshot_file_path).
    """
    path = snapshot_path(scheme_name, snapshots_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not force_fetch:
        html = path.read_text(encoding="utf-8")
        if not html.strip():
            raise ValueError(f"Empty snapshot file: {path}")
        return html, path

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        timeout=REQUEST_TIMEOUT_S,
    )
    response.raise_for_status()
    html = response.text
    if not html.strip():
        raise ValueError(f"Empty HTTP response for {url}")

    path.write_text(html, encoding="utf-8")
    return html, path


def load_documents(
    *,
    csv_path: Path | None = None,
    snapshots_dir: Path | None = None,
    force_fetch: bool = False,
) -> list[dict[str, Any]]:
    """
    Load all sources into cleaned document dicts:

    {text, source_url, scheme_name, category, ingested_at}
    """
    sources = load_sources(csv_path)
    ingested_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    documents: list[dict[str, Any]] = []

    for row in sources:
        html, _ = fetch_or_read_snapshot(
            row["url"],
            row["scheme_name"],
            snapshots_dir=snapshots_dir,
            force_fetch=force_fetch,
        )
        text = html_to_text(html)
        if not text or len(text) < 50:
            raise ValueError(
                f"Page text empty/too short after cleaning for "
                f"{row['scheme_name']!r} ({row['url']}). "
                f"Got {len(text)} chars — page may be JS-rendered; "
                f"check snapshot under data/snapshots/."
            )

        documents.append(
            {
                "text": text,
                "source_url": row["url"],
                "scheme_name": row["scheme_name"],
                "category": row["category"],
                "ingested_at": ingested_at,
            }
        )

    return documents


if __name__ == "__main__":
    docs = load_documents()
    exported = export_raw_documents(docs)
    print(f"Loaded {len(docs)} documents\n")
    for doc in docs:
        print(f"{doc['scheme_name']}: {len(doc['text'])} chars [{doc['category']}]")
    print(f"\nRaw text exported to data/raw/ ({len(exported)} files)")
