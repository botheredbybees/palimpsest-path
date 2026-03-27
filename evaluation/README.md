# Evaluation

This directory holds print-ready evaluation instruments and the companion data spreadsheet for the Palimpsest Path project.

See `docs/section-09-evaluation.md` for the full instrument descriptions, form text, and coding instructions.

---

## Instruments

| File | Format | Purpose |
|------|--------|---------|
| `weekly-coding-sheet.md` | Markdown / print | Photo-narrative weekly coding sheet (one per week, Weeks 1–8) |
| `thematic-register.md` | Markdown / print | Running thematic analysis register (begin Week 4) |
| `Evaluation_Data.xlsx` | Excel | ESP32 daily log, Happiness Index coding log, SROI calculator |

---

## Printing Instructions

### Weekly Coding Sheet (`weekly-coding-sheet.md`)
- Print 10 copies before the project begins (8 intervention weeks + 2 spares)
- Print single-sided for easy field use
- File completed sheets with the corresponding week's photograph set

### Thematic Register (`thematic-register.md`)
- Print one copy at the start of Week 4
- Keep it in your site visit kit from Week 4 onwards
- Update during or immediately after each Sunday evening coding session

---

## Spreadsheet: Evaluation_Data.xlsx

The spreadsheet contains three sheets:

### Sheet 1: ESP32 Daily Log
- One row per valid pedestrian event
- Fields: date, week, unit_id, transit_s, category (transit / slow / dwell), rain_flag
- Weekly summary rows auto-calculated via formula

### Sheet 2: Happiness Index Coding Log
- One row per weekday photograph (Weeks 3–8)
- Fields: date, week, bar_count, median_height, distribution_band, rain_reset_flag, annotations
- Weekly median and mean auto-calculated

### Sheet 3: SROI Calculator
- Inputs: total pedestrian count, engagement events, bar count, QR scans
- Proxy values (after Fancourt & Finn, 2019): pre-loaded, adjustable
- Output: illustrative SROI ratio with stated assumptions

---

## Coding Schedule

| When | What |
|------|------|
| Each morning (site visit) | Photograph chalk surface. Download sensor data if scheduled. Log happiness index bars. Log rain events. |
| Each Sunday evening | Complete weekly coding sheet. Update thematic register (from Week 4). Enter data into Evaluation_Data.xlsx. |
| After Week 4 | Review all coded photos. Identify initial emergent themes. Begin thematic register. |
| After Week 8 | Final photo set coded. Begin narrative arc analysis. Draft qualitative findings. |
| After Week 10 | Complete SROI calculator. Compile evaluation report. |
