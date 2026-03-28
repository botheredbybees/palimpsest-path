#!/usr/bin/env python3
"""
deploy_pages.py
Reads all .md files from site/ and creates or updates matching WordPress pages.

Each markdown file must begin with a YAML front matter block:
---
title: Page Title
slug: page-slug
status: draft   # or publish
order: 10       # menu order (optional)
---

The script matches pages by slug. If a page with that slug exists it is
updated; if not, a new page is created.

Environment variables required:
  WP_BASE_URL      e.g. https://sidewalkcircus.org
  WP_USERNAME      WordPress admin username
  WP_APP_PASSWORD  WordPress application password
"""

import os
import re
import sys
import requests
import markdown
from pathlib import Path

WP_BASE_URL = os.environ["WP_BASE_URL"].rstrip("/")
WP_USERNAME = os.environ["WP_USERNAME"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"].replace(" ", "")

API_BASE = f"{WP_BASE_URL}/wp-json/wp/v2"
AUTH = (WP_USERNAME, WP_APP_PASSWORD)
SITE_DIR = Path(__file__).parent.parent.parent / "site"

SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
})


def parse_front_matter(text):
    """Extract YAML-style front matter and body from a markdown string."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        raise ValueError("No front matter found. Each site/*.md must start with ---")
    front = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            front[key.strip()] = value.strip()
    body = text[match.end():]
    return front, body


def get_existing_pages():
    """Return a dict of slug → page_id for all existing WordPress pages."""
    pages = {}
    page = 1
    while True:
        r = SESSION.get(
            f"{API_BASE}/pages",
            auth=AUTH,
            params={"per_page": 100, "page": page, "status": "publish,draft,pending,private"},
        )
        if r.status_code == 400:
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        for p in batch:
            pages[p["slug"]] = p["id"]
        page += 1
    return pages


def deploy_page(front, html_content, existing_pages):
    slug = front.get("slug", "")
    if not slug:
        raise ValueError("Front matter must include a 'slug' field")

    payload = {
        "title": front.get("title", slug),
        "slug": slug,
        "content": html_content,
        "status": front.get("status", "draft"),
        "menu_order": int(front.get("order", 0)),
    }

    if slug in existing_pages:
        page_id = existing_pages[slug]
        r = SESSION.post(f"{API_BASE}/pages/{page_id}", auth=AUTH, data=payload)
        action = "Updated"
    else:
        r = SESSION.post(f"{API_BASE}/pages", auth=AUTH, data=payload)
        action = "Created"

    r.raise_for_status()
    page_url = r.json().get("link", "")
    print(f"  {action}: [{slug}] {front.get('title', '')} → {page_url}")
    return r.json()


def main():
    md_files = sorted(SITE_DIR.glob("*.md"))
    if not md_files:
        print("No .md files found in site/")
        sys.exit(1)

    print(f"Connecting to {WP_BASE_URL} as {WP_USERNAME}...")
    existing_pages = get_existing_pages()
    print(f"Found {len(existing_pages)} existing page(s) on site.")

    errors = []
    for md_path in md_files:
        try:
            text = md_path.read_text(encoding="utf-8")
            front, body = parse_front_matter(text)
            html = markdown.markdown(
                body,
                extensions=["tables", "fenced_code", "nl2br"],
            )
            deploy_page(front, html, existing_pages)
        except Exception as e:
            print(f"  ERROR processing {md_path.name}: {e}")
            errors.append(md_path.name)

    if errors:
        print(f"\nFailed: {errors}")
        sys.exit(1)
    else:
        print(f"\nAll {len(md_files)} page(s) deployed successfully.")


if __name__ == "__main__":
    main()
