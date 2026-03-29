#!/usr/bin/env python3
"""
upload.py — local WordPress page deployer for Palimpsest Path

Reads all site/*.md files, converts them to HTML, and creates or updates
the matching WordPress pages via the REST API.

Credentials are loaded from a .env file in the repo root (or from
environment variables if already set):

  WP_BASE_URL      e.g. https://sidewalkcircus.org
  WP_USERNAME      WordPress admin username
  WP_APP_PASSWORD  WordPress application password (spaces optional)

Usage:
  python upload.py           # deploy all site/*.md files
  python upload.py about.md  # deploy a single file
"""

import os
import re
import sys
import requests
import markdown
from pathlib import Path

# ---------------------------------------------------------------------------
# Credentials — load from .env if present, fall back to environment
# ---------------------------------------------------------------------------
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

try:
    WP_BASE_URL    = os.environ["WP_BASE_URL"].rstrip("/")
    WP_USERNAME    = os.environ["WP_USERNAME"]
    WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"].replace(" ", "")
except KeyError as e:
    sys.exit(f"Missing required credential: {e}. Add it to .env or set as an environment variable.")

API_BASE = f"{WP_BASE_URL}/wp-json/wp/v2"
AUTH     = (WP_USERNAME, WP_APP_PASSWORD)
SITE_DIR = Path(__file__).parent / "site"

SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Origin": WP_BASE_URL,
    "Referer": f"{WP_BASE_URL}/wp-admin/",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def youtube_id(url):
    """Extract a YouTube video ID from watch, short, or embed URLs."""
    m = re.search(r'[?&]v=([^&]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'youtu\.be/([^?&/]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'youtube\.com/embed/([^?&/]+)', url)
    if m:
        return m.group(1)
    return None


def convert_video_embeds(body):
    """Convert !video[Title](URL) markers to YouTube iframe HTML.

    Syntax in .md files:
        !video[Descriptive title](https://www.youtube.com/watch?v=XXXX)

    Falls back to a plain hyperlink for non-YouTube URLs.
    """
    def replace(m):
        title = m.group(1)
        url   = m.group(2)
        vid_id = youtube_id(url)
        if vid_id:
            embed_url = f"https://www.youtube.com/embed/{vid_id}"
            return (
                f'<figure class="wp-block-embed is-type-video">'
                f'<div class="wp-block-embed__wrapper">'
                f'<iframe width="560" height="315" '
                f'src="{embed_url}" title="{title}" frameborder="0" '
                f'allow="accelerometer; autoplay; clipboard-write; '
                f'encrypted-media; gyroscope; picture-in-picture" '
                f'allowfullscreen></iframe>'
                f'</div>'
                f'<figcaption>{title}</figcaption>'
                f'</figure>'
            )
        return f'<p><a href="{url}">{title}</a></p>'

    return re.sub(r'!video\[([^\]]+)\]\(([^)]+)\)', replace, body)


def parse_front_matter(text):
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        raise ValueError("No YAML front matter found — each site/*.md must start with ---")
    front = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            front[key.strip()] = value.strip()
    body = text[match.end():]
    return front, body


def fetch_pages_by_status(status):
    """Return slug → id for all pages with the given status."""
    found = {}
    page = 1
    while True:
        r = SESSION.get(
            f"{API_BASE}/pages",
            auth=AUTH,
            params={"per_page": 100, "page": page, "status": status},
        )
        if r.status_code == 400:   # no more pages
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        for p in batch:
            found[p["slug"]] = p["id"]
        page += 1
    return found


def get_existing_pages():
    """Return slug → id, with published pages taking priority over drafts."""
    drafts    = fetch_pages_by_status("draft")
    published = fetch_pages_by_status("publish")
    return {**drafts, **published}   # published overwrites draft on conflict


def deploy_page(front, html_content, existing_pages):
    slug = front.get("slug", "")
    if not slug:
        raise ValueError("Front matter must include a 'slug' field")

    payload = {
        "title":      front.get("title", slug),
        "slug":       slug,
        "content":    html_content,
        "status":     front.get("status", "draft"),
        "menu_order": int(front.get("order", 0)),
    }

    if slug in existing_pages:
        page_id = existing_pages[slug]
        r = SESSION.post(f"{API_BASE}/pages/{page_id}", auth=AUTH, json=payload)
        action = "Updated"
    else:
        r = SESSION.post(f"{API_BASE}/pages", auth=AUTH, json=payload)
        action = "Created"

    if not r.ok:
        print(f"    HTTP {r.status_code}: {r.text[:500]}")
    r.raise_for_status()
    data = r.json()
    existing_pages[data["slug"]] = data["id"]   # keep map fresh within a run
    print(f"  {action}: /{slug}  →  {data.get('link', '')}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Allow optional single-file argument: python upload.py about.md
    if len(sys.argv) > 1:
        md_files = [SITE_DIR / sys.argv[1]]
        for f in md_files:
            if not f.exists():
                sys.exit(f"File not found: {f}")
    else:
        md_files = sorted(SITE_DIR.glob("*.md"))

    if not md_files:
        sys.exit(f"No .md files found in {SITE_DIR}")

    print(f"Connecting to {WP_BASE_URL} as {WP_USERNAME}...")
    existing = get_existing_pages()
    print(f"Found {len(existing)} existing page(s): {', '.join(sorted(existing))}\n")

    errors = []
    for md_path in md_files:
        print(f"  {md_path.name}")
        try:
            text = md_path.read_text(encoding="utf-8")
            front, body = parse_front_matter(text)
            body = convert_video_embeds(body)
            html = markdown.markdown(body, extensions=["tables", "fenced_code", "nl2br"])
            deploy_page(front, html, existing)
        except Exception as e:
            print(f"    ERROR: {e}")
            errors.append(md_path.name)

    print()
    if errors:
        print(f"Failed: {errors}")
        sys.exit(1)
    else:
        print(f"Done — {len(md_files)} page(s) deployed.")


if __name__ == "__main__":
    main()
