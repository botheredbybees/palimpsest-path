#!/usr/bin/env python3
"""
fetch_bird_photos.py — populate birdlife.md with iNaturalist observation photos

For each species in data/birds.yml, queries the iNaturalist API to find a
CC-licensed observation photo, preferring photos from the Palimpsest Path
project (project_id=283091) and falling back to any Tasmanian observation.

Replaces the '*[Your photo here]*' placeholder in each species entry with
a linked image and observer attribution.

Usage:
    python fetch_bird_photos.py           # update site/birdlife.md in place
    python fetch_bird_photos.py --dry-run # print what would change, no writes
"""

import re
import sys
import time
import requests
from pathlib import Path

PROJECT_ID       = 283091   # palimpsest-path-project on iNaturalist
TASMANIA_PLACE_ID = 7853    # iNaturalist place_id for Tasmania
PHOTO_PLACEHOLDER = "*[Your photo here]*"
BIRDLIFE_MD      = Path(__file__).parent / "site" / "birdlife.md"
BIRDS_YML        = Path(__file__).parent / "data" / "birds.yml"

# CC licences we are willing to hotlink and attribute
CC_LICENCES = "cc-by,cc-by-nc,cc-by-sa,cc-by-nc-sa,cc-by-nd,cc-by-nc-nd,cc0"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "palimpsest-path-site/1.0 (sidewalkcircus.org)",
    "Accept": "application/json",
})


def inat_get(endpoint, params):
    """GET from iNaturalist API v1 with a courtesy 1-second delay."""
    time.sleep(1)
    r = SESSION.get(f"https://api.inaturalist.org/v1/{endpoint}", params=params)
    r.raise_for_status()
    return r.json()


def find_photo(scientific_name, project_id=None, place_id=None):
    """
    Return (photo_url, attribution, observation_url) for the highest-voted
    CC-licensed observation of scientific_name, or None if not found.
    """
    params = {
        "taxon_name":  scientific_name,
        "has_photos":  "true",
        "per_page":    1,
        "order_by":    "votes",
        "order":       "desc",
        "license":     CC_LICENCES,
        "photo_license": CC_LICENCES,
    }
    if project_id:
        params["project_id"] = project_id
    if place_id:
        params["place_id"] = place_id

    try:
        data = inat_get("observations", params)
    except requests.HTTPError as e:
        print(f"    API error: {e}")
        return None

    results = data.get("results", [])
    if not results:
        return None

    obs    = results[0]
    photos = obs.get("photos", [])
    if not photos:
        return None

    photo = photos[0]
    # Prefer the stable open-data S3 URL; replace square thumbnail with medium
    url   = photo.get("url", "").replace("/square.", "/medium.")
    attr  = photo.get("attribution", "")
    obs_url = f"https://www.inaturalist.org/observations/{obs['id']}"
    return url, attr, obs_url


def load_species():
    """Parse data/birds.yml without a YAML dependency."""
    species, current = [], {}
    for line in BIRDS_YML.read_text(encoding="utf-8").splitlines():
        line = line.rstrip()
        if line.startswith("- common_name:"):
            if current:
                species.append(current)
            current = {"common_name": line.split(":", 1)[1].strip()}
        elif line.startswith("  scientific_name:"):
            current["scientific_name"] = line.split(":", 1)[1].strip()
    if current:
        species.append(current)
    return species


def main():
    dry_run = "--dry-run" in sys.argv

    species_list = load_species()
    text         = BIRDLIFE_MD.read_text(encoding="utf-8")
    updated      = 0

    for sp in species_list:
        name = sp["common_name"]
        sci  = sp.get("scientific_name", "")
        if not sci:
            continue

        # Scope the search to the heading for this species so we only replace
        # the correct placeholder, not one belonging to a different entry.
        heading_pat = re.compile(
            rf"(### {re.escape(name)}\n[\s\S]*?){re.escape(PHOTO_PLACEHOLDER)}",
        )
        if not heading_pat.search(text):
            print(f"  {name}: placeholder already replaced or heading not found — skipping")
            continue

        print(f"  {name} ({sci})")

        # 1. Try project photos first
        print(f"    → searching project {PROJECT_ID}...", end=" ", flush=True)
        result = find_photo(sci, project_id=PROJECT_ID)
        if result:
            print("found ✓")
        else:
            # 2. Fall back to any Tasmanian observation
            print("not found")
            print(f"    → searching Tasmania-wide...", end=" ", flush=True)
            result = find_photo(sci, place_id=TASMANIA_PLACE_ID)
            if result:
                print("found ✓")
            else:
                print("no CC photo found — leaving placeholder")
                continue

        photo_url, attribution, obs_url = result
        print(f"    {obs_url}")

        replacement = (
            f"[![{name}]({photo_url})]({obs_url})\n"
            f"*Photo: {attribution} — [view observation on iNaturalist]({obs_url})*"
        )

        text = heading_pat.sub(
            lambda m, r=replacement: m.group(1) + r,
            text,
            count=1,
        )
        updated += 1

    print(f"\n{updated} photo(s) inserted.")

    if dry_run:
        print("--- DRY RUN: no files written ---")
    else:
        BIRDLIFE_MD.write_text(text, encoding="utf-8")
        print(f"Written: {BIRDLIFE_MD}")
        print("Run  python upload.py birdlife.md  to deploy.")


if __name__ == "__main__":
    main()
