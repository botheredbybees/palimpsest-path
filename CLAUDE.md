# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Palimpsest Path is a community chalk art project on the Cygnet Boardwalk, Tasmania. The repository spans three independent technical domains:

1. **Embedded firmware** (`firmware/`) — MicroPython for two Raspberry Pi Pico sensor units (not Python 3; no pip; runs on hardware)
2. **Data analysis pipeline** (`analysis/`) — CPython 3.9+ using pandas, scikit-learn, matplotlib
3. **WordPress site content** (`site/`) — Markdown pages deployed to `sidewalkcircus.org` via REST API

These three domains share no runtime; firmware code cannot use CPython libraries and vice versa.

## Commands

### Analysis pipeline

```bash
pip install pandas scikit-learn matplotlib numpy
python analysis/analysis.py          # run the full pipeline
pytest analysis/                     # run unit tests
pytest analysis/tests/test_analysis.py::test_classify_walker  # run a single test
```

Before the first analysis run, edit the `USER CONFIGURATION` block at the top of `analysis/analysis.py` to set `DATA_DIR`, `INTERVENTION_START`, and `POST_INT_START`.

### WordPress deployment (local)

```bash
pip install requests markdown
python upload.py            # deploy all site/*.md pages
python upload.py about.md   # deploy a single page
```

Requires a `.env` file in the repo root (copy `.env.example` → `.env` and fill in values). The GitHub Actions workflow (`deploy-to-wordpress.yml`) is manual-trigger only — Bluehost ModSecurity blocks automated REST API POSTs.

### Fetch bird photos

```bash
python fetch_bird_photos.py
```

## Architecture

### Site content → WordPress

Each `site/*.md` file maps 1:1 to a WordPress page. Files must begin with YAML front matter:

```
---
title: Page Title
slug: page-slug
status: publish   # or draft
order: 10
---
```

`upload.py` is the canonical local deployer (supports `.env`, handles video embeds via `!video[Title](URL)` syntax, prioritises published pages over drafts on slug conflict). `.github/workflows/deploy_pages.py` is a simpler CI variant that reads credentials only from environment variables.

### Sensor data flow

```
SD card (UNIT_A + UNIT_B CSVs)
  → data/raw/UNIT_A/*.csv
  → data/raw/UNIT_B/*.csv
  → analysis/analysis.py
      match_events()     — pair inbound (A) + outbound (B) within 5-min window
      classify_walker()  — jogger / regular_walker / slow_walker (transit_ms)
      classify_dwell()   — Transit / Pause / Dwell (dwell_time_s)
      DBSCAN cluster     — find natural behavioural groups
      aggregate_weekly() — weekly medians and proportions
  → data/analysis/figures/*.png
  → data/processed/weekly-summary.csv
```

Raw sensor data (`data/raw/`) is gitignored. Copy SD card directories manually before running the pipeline.

### Firmware

`firmware/config.py` is the only file that differs between the two physical units (`UNIT_ID = "UNIT_A"` vs `"UNIT_B"`). All other firmware files are identical. `sdcard.py` is a third-party MicroPython driver (not in the standard Pico image) — download from `micropython/micropython-lib`.

Run `firmware/test_sensors.py` via USB REPL before sealing each unit. It tests the DS3231 RTC, both IR sensors, and SD card read/write.

## Key constraints

- The GitHub Actions deploy is **manual-trigger only** — do not change `on:` to `push` triggers.
- `data/raw/` is gitignored — never assume raw sensor CSVs exist in the repo.
- WordPress pages are matched by slug; changing a slug in front matter creates a new page rather than renaming the existing one.
- Firmware is MicroPython — standard CPython modules (`os.path`, `datetime`, etc.) may not be available; use `uos`, `utime`, etc.
