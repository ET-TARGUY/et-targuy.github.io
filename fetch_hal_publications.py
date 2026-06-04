#!/usr/bin/env python3
"""
Fetch publications from HAL API and generate Jekyll-compatible .md files.
Usage: python fetch_hal_publications.py --hal-id YOUR_HAL_ID
"""

import argparse
import json
import os
import re
import requests
from datetime import datetime
from pathlib import Path

HAL_API = "https://api.archives-ouvertes.fr/search/"

FIELDS = [
    "halId_s",
    "title_s",
    "abstract_s",
    "producedDate_s",
    "publicationDateY_i",
    "docType_s",
    "journalTitle_s",
    "conferenceTitle_s",
    "bookTitle_s",
    "publisher_s",
    "uri_s",
    "authFullName_s",
    "keyword_s",
    "files_s",
]

# Map HAL doc types to publication_category keys used in your Jekyll site
CATEGORY_MAP = {
    "ART": "journal",
    "COMM": "conference",
    "POSTER": "conference",
    "THESE": "thesis",
    "REPORT": "other",
    "PREPRINT": "preprint",
    "OTHER": "other",
}


def fetch_publications(hal_id: str) -> list[dict]:
    params = {
        "q": f"authIdHal_s:{hal_id}",
        "fl": ",".join(FIELDS),
        "wt": "json",
        "rows": 100,
        "sort": "producedDate_s desc",
    }
    resp = requests.get(HAL_API, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", {}).get("docs", [])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:80]


def get_venue(doc: dict) -> str:
    return (
        doc.get("journalTitle_s")
        or doc.get("conferenceTitle_s")
        or doc.get("bookTitle_s")
        or doc.get("publisher_s")
        or ""
    )


def make_md(doc: dict) -> tuple[str, str]:
    """Returns (filename, markdown_content)."""
    hal_id = doc.get("halId_s", "unknown")
    title = (doc.get("title_s") or ["Untitled"])[0]
    year = doc.get("publicationDateY_i") or datetime.now().year
    date_str = doc.get("producedDate_s", f"{year}-01-01")[:10]
    doc_type = doc.get("docType_s", "OTHER")
    category = CATEGORY_MAP.get(doc_type, "other")
    venue = get_venue(doc)
    authors = ", ".join(doc.get("authFullName_s") or [])
    abstract = (doc.get("abstract_s") or [""])[0]
    url = doc.get("uri_s", "")
    keywords = doc.get("keyword_s") or []
    pdf = (doc.get("files_s") or [""])[0]

    # Escape special YAML chars in title
    title_safe = title.replace('"', '\\"')

    frontmatter = f"""---
title: "{title_safe}"
collection: publications
category: {category}
permalink: /publication/{hal_id}
date: {date_str}
venue: "{venue}"
authors: "{authors}"
excerpt: "{abstract[:200].replace(chr(10), ' ')}"
paperurl: "{url}"
"""
    if pdf:
        frontmatter += f'pdfurl: "{pdf}"\n'
    if keywords:
        frontmatter += f"tags: {json.dumps(keywords)}\n"

    frontmatter += "---\n"

    body = f"{abstract}\n" if abstract else ""
    if url:
        body += f"\n[View on HAL]({url})\n"

    slug = slugify(f"{date_str}-{title}")
    filename = f"{slug}.md"
    return filename, frontmatter + body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hal-id", required=True, help="Your HAL author ID")
    parser.add_argument(
        "--output-dir",
        default="_publications",
        help="Output directory (default: _publications)",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(exist_ok=True)

    print(f"Fetching publications for HAL ID: {args.hal_id}")
    docs = fetch_publications(args.hal_id)
    print(f"Found {len(docs)} publications")

    # Clear existing auto-generated files (those with hal_ prefix)
    for f in out_dir.glob("*.md"):
        if f.name.startswith("hal_"):
            f.unlink()

    for doc in docs:
        filename, content = make_md(doc)
        filepath = out_dir / f"hal_{filename}"
        filepath.write_text(content, encoding="utf-8")
        print(f"  Written: {filepath.name}")

    print("Done.")


if __name__ == "__main__":
    main()
