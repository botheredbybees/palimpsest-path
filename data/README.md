# Data

This directory holds sensor logs, rain event records, and analysis outputs generated during the Palimpsest Path project.

---

## Directory Structure (when live)

```
data/
├── README.md               # This file
├── rain-log.md             # Manual rain event log (date, time, severity, notes)
├── raw/                    # Raw SD card dumps from sensor units (excluded from git — see .gitignore)
│   ├── unit-a/             # UNIT_A CSV files (one per day)
│   └── unit-b/             # UNIT_B CSV files (one per day)
├── processed/              # Cleaned and classified data
│   ├── dwell-times.csv     # Merged, classified transit events
│   └── weekly-summary.csv  # Aggregated weekly stats
└── analysis/               # Output charts and SROI calculations
    ├── figures/            # PNG/SVG chart exports
    └── sroi-calculator.xlsx
```

---

## Data Collection Protocol

See `docs/section-08-data-analysis.md` for full analytical framework.

### Daily (during site visit)
1. Check sensor unit enclosures — log any hardware anomalies
2. Download SD card if approaching capacity, or on scheduled weekly swap day
3. Log any rain events in `rain-log.md`
4. Back up downloaded files to two locations before re-using SD card

### Weekly (Sunday evening)
1. Run classification script on the week's raw CSVs
2. Append results to `processed/dwell-times.csv`
3. Update `processed/weekly-summary.csv`
4. Note any invalid days (hardware failure, extended rain) in the summary

---

## Rain Event Log Format

`rain-log.md` uses a simple table:

| Date | Approx. Start | Approx. End | Severity | Effect on chalk | Notes |
|------|--------------|-------------|----------|-----------------|-------|
| DD/MM/YYYY | HH:MM | HH:MM | Light / Moderate / Heavy | None / Partial / Full washout | |

---

## Data Retention

- Raw CSV files are never edited or deleted
- All analysis operates on copies in `processed/`
- If a card is corrupted: note the outage window in this README and exclude those days from valid measurement count
- Do not attempt data recovery unless straightforward — partial data is worse than no data for statistical integrity

---

## Phase Log

| Phase | Start Date | End Date | Valid Days | Notes |
|-------|-----------|---------|------------|-------|
| Phase 0 (baseline) | | | | Minimum 10 valid days required before Week 1 |
| Week 1 | | | | |
| Week 2 | | | | |
| Week 3 | | | | Happiness Index begins |
| Week 4 | | | | |
| Week 5 | | | | |
| Week 6 | | | | |
| Week 7 | | | | |
| Week 8 | | | | |
| Week 9 (post) | | | | |
| Week 10 (post) | | | | |
