# Section 5: Digital Infrastructure

*Web, QR & Data Pipeline Architecture — sidewalkcircus.org*

---

## 5.1 System Overview

The Palimpsest Path uses two distinct digital systems that operate in parallel throughout the project. The first is a public-facing web presence at sidewalkcircus.org, built on WordPress, that hosts the photo-narrative gallery, participant information, and QR code landing pages. The second is a local, offline sensor network of Raspberry Pi Pico W microcontrollers that logs pedestrian transit and dwell-time data to SD card, with no internet connectivity and no personally identifiable data collection.

These systems are deliberately kept separate. The web presence is outward-facing and participatory; the sensor network is inward-facing and analytical. They share no data in real time. Integration happens only at the analysis stage, when timestamped sensor logs are compared against the weekly photographic archive.

| System | Details |
|--------|---------|
| **sidewalkcircus.org** | Platform: WordPress (self-hosted on Bluehost). Purpose: public gallery, QR landing pages, participation instructions, privacy/consent. Data: photos, participant submissions, weekly archive posts. Access: public-facing, no login required for viewing. Must be live and tested before QR signage is printed in Phase 0. |
| **Pico W Sensor Array** | Platform: Raspberry Pi Pico W microcontrollers running MicroPython. Purpose: measure pedestrian transit and dwell times. Data: timestamped IR beam-break events, logged to local SD card only. Access: offline, no Wi-Fi transmission, no cloud, no personally identifiable data. Must be installed and logging before Phase 0 baseline begins. |

---

## 5.2 WordPress: sidewalkcircus.org

### Site Architecture

The site requires four core pages and one recurring post type, all buildable in a standard WordPress installation with no custom development:

| Page / Type | URL Slug | Content |
|-------------|---------|---------|
| **About** | /about | Plain-language project description, participant information, privacy and consent statement, contact details for project lead. |
| **Participate** | /participate | Current week's prompt, chalk station locations, how-to instructions with example photos, QR code image for sharing. |
| **Gallery** | /gallery | Full chronological photo archive, browsable by week. Lightbox display recommended. |
| **Privacy** | /privacy | Formal privacy and consent statement. Linked from all QR landing pages. Must be live before signage goes up. |
| **Weekly Post (recurring)** | /week-N | Posted each Sunday. Three to five photos, brief caption, current prompt, link to gallery. Categories: Week 1–8, Rain Events, Community Highlights. |

### Recommended Plugins

| Plugin | Purpose |
|--------|---------|
| **Photo gallery** | Envira Gallery or similar: lightbox display, category filtering by week, mobile-responsive. Alternative: native WordPress block gallery is sufficient if plugin installation is not preferred. |
| **Upload / submission** | WPForms (free tier) or Gravity Forms: simple photo upload form for participant submissions. Set form to require consent checkbox before submission. All uploads held for moderation before publication. |
| **QR code generation** | QR Code Generator plugin, or generate externally at qr-code-generator.com and embed as image. Generate one QR per destination: /participate (for boardwalk signage) and /gallery (for shop window cards). Test each QR code on multiple devices before printing signage. |
| **SEO & sharing** | Yoast SEO (free): ensures gallery posts have correct Open Graph metadata for social sharing. Set featured image on every weekly post so shared links display a photo thumbnail. |

### Privacy & Consent Framework

The following statement must appear on the /privacy page and be linked from all QR landing pages. Wording should be reviewed by the FXA301 supervisor before the site goes live:

---

**Privacy Statement — The Palimpsest Path**

No cameras are used in this project. The sensor devices on the boardwalk count pedestrian movements using infrared beams only. No images, faces, voices, or personal identifying information are collected by the sensors.

Photos submitted to this gallery are voluntary. By submitting a photo, you consent to it being published on this site and used in academic research related to the project. You may request removal at any time by contacting the project lead.

Chalk contributions on the boardwalk are public artworks. They may be photographed as part of the project archive. If you do not wish your contribution to be photographed, please indicate this with a chalk X next to your mark.

---

## 5.3 QR Code Workflow

Three distinct QR codes serve different functions in the project. Each should be generated, tested, and printed before Phase 0 ends:

| QR Code | Destination | Physical Location | Purpose |
|---------|------------|-------------------|---------|
| **Boardwalk Sign A** | sidewalkcircus.org/participate | Gallery entrance signage (top of 100m section) | Primary participant onboarding: explains project, shows current prompt, links to how-to. |
| **Boardwalk Sign B** | sidewalkcircus.org/gallery | Gallery exit signage (bottom of 100m section) | Encourages walkers to view the full archive after engaging with the chalk. |
| **Shop / Library Card** | sidewalkcircus.org/about | Shopkeeper windows, library display, Arts Council materials | Community awareness and off-site discovery. |

**Signage design guidelines:**
- Print on weatherproof material (laminated A5 or UV-printed aluminium composite for outdoor use).
- QR code minimum print size: 4cm × 4cm. Test scan from 50cm before finalising print run.
- Signage text should carry only: project name, one-line description, QR code, and the phrase "scan to participate." Do not include theoretical framework on physical signage.
- Include the privacy statement URL in small text beneath each QR code: sidewalkcircus.org/privacy

---

## 5.4 Pico W Sensor Network: Architecture

The attention tracker uses a pair of Raspberry Pi Pico W microcontrollers positioned at the start and end of the 100m gallery section. Each unit hosts a dual infrared beam counter: two IR emitter/receiver pairs spaced approximately 30cm apart, oriented perpendicular to pedestrian flow. The direction of travel is determined by the sequence in which beams are broken.

All data is logged to a local microSD card. There is no Wi-Fi transmission, no cloud storage, and no network connectivity during operation. This "Privacy by Design" architecture means the system cannot collect data beyond what it is physically capable of measuring: beam-break timestamps and direction.

### Hardware Components

| Component | Specification | Qty | Notes |
|-----------|--------------|-----|-------|
| **Microcontroller** | Raspberry Pi Pico W | 2 | One per end of gallery section. MicroPython firmware. Lower power draw and simpler toolchain than ESP32. |
| **IR sensor pairs** | E18-D80NK IR proximity sensors | 4 pairs (8 units) | Two pairs per unit for directional detection. E18-D80NK preferred for outdoor range (up to 80cm). |
| **SD card module** | SPI microSD adapter module | 2 | One per microcontroller. Standard SPI wiring. |
| **MicroSD cards** | 8GB Class 10 microSD | 4 | 2 active + 2 spares for weekly swap. Ample for 10+ weeks of timestamped logs at low data volume. |
| **Power supply** | 18650 LiPo battery + TP4056 charge module | 2 sets | Battery preferred for weatherproof enclosure. Estimate 5–7 days per charge at low duty cycle. |
| **Enclosure** | IP65-rated weatherproof ABS enclosure, min 100×100×60mm | 2 | Cable glands for sensor wires. Mount to boardwalk bannister with stainless steel brackets. |
| **RTC module** | DS3231 real-time clock module | 2 | Maintains accurate timestamps independent of power interruptions. |

### Data Logging Format

Each beam-break event is logged as a single CSV row to the SD card. Log files are named by date (`YYYY-MM-DD.csv`) and appended continuously:

```
timestamp, unit_id, direction, beam, transit_ms
2025-06-02 07:43:11, UNIT_A, INBOUND, BEAM_1, NULL
2025-06-02 07:43:11, UNIT_A, INBOUND, BEAM_2, 1840
2025-06-02 07:43:14, UNIT_A, OUTBOUND, BEAM_2, NULL
2025-06-02 07:43:15, UNIT_A, OUTBOUND, BEAM_1, 980
```

**Field definitions:**
- `timestamp` — DS3231 RTC datetime, accurate to ±1 second
- `unit_id` — UNIT_A (gallery entrance) or UNIT_B (gallery exit)
- `direction` — INBOUND (entering gallery) or OUTBOUND (exiting). Determined by beam break sequence.
- `beam` — which of the two beams was broken (BEAM_1 = outer, BEAM_2 = inner)
- `transit_ms` — milliseconds between the two beam breaks on the same pass. NULL on first beam break; populated on second. Used to classify walker type (jogger / walker / participant).

### Dwell-Time Calculation

Dwell time — the primary metric for the intervention's effect — is calculated from the time elapsed between a pedestrian's INBOUND event at UNIT_A and their OUTBOUND event at UNIT_B (or vice versa):

```
dwell_time = UNIT_B.timestamp(OUTBOUND) - UNIT_A.timestamp(INBOUND)

Classification thresholds (tuned from baseline data):

transit_ms < 800       → Jogger / cyclist
transit_ms 800–2500    → Regular walker
transit_ms > 2500      → Slow walker / participant candidate

dwell_time < 30s       → Transit (no engagement)
dwell_time 30s–120s    → Pause (possible engagement)
dwell_time > 120s      → Dwell (probable engagement)
```

> Note: transit_ms thresholds are initialised from published pedestrian speed research (approximately 1.4 m/s average walking speed over a 30cm beam spacing = ~215ms). These thresholds should be calibrated against the first week of baseline observations, where manual observation and sensor data can be compared directly.

### Firmware Overview

The firmware runs on MicroPython on the Pico W. The core loop is:

```
setup:
  initialise RTC (DS3231 via I2C)
  mount SD card (SPI)
  configure IR sensor pins as interrupts
  open today's log file (YYYY-MM-DD.csv)

loop:
  on IR interrupt:
    record timestamp from RTC
    determine which beam (BEAM_1 or BEAM_2)
    determine direction from beam sequence
    calculate transit_ms if second beam in pair
    append CSV row to log file
    flush to SD (prevents data loss on power interruption)

  every 6 hours:
    log system health (battery voltage, SD free space)
    rotate log file if date has changed
```

*Full firmware code is provided in the Technical Appendix (`docs/technical-appendix.md`).*

---

## 5.5 Data Retrieval & Management

| Task | Protocol |
|------|---------|
| **Retrieval schedule** | Remove SD cards weekly for data download. Swap with formatted spare cards to minimise downtime. Download CSV files to local computer. Back up to a second location (external drive or private cloud folder) immediately. Do not delete logs from SD cards until backup is confirmed. |
| **File naming convention** | Rename downloaded files on import: `PALIMPSEST_UNIT-A_YYYY-MM-DD.csv`. Maintain a master log folder structure: `/data/raw/unit-a/` and `/data/raw/unit-b/`. Never edit raw files. All analysis should operate on copies. |
| **Battery maintenance** | Check battery voltage in system health logs each week. Recharge or swap batteries on the same visit as SD card retrieval. Log any power interruptions in the project log with timestamp — these create gaps in the sensor record that must be noted in the analysis. |
| **Hardware checks** | Inspect enclosure seals and cable glands after heavy rain. Verify IR beam alignment weekly: walk through the beam path and confirm events are logged. If a unit fails: note the outage period in the project log and exclude those days from valid measurement counts. |

---

## 5.6 Integration: Sensor Data & Photo Archive

The sensor logs and the photo archive are maintained as independent datasets throughout the project. Integration occurs only at the analysis stage (see `docs/section-08-data-analysis.md`), where dwell-time distributions from each week are compared against the photographic record of chalk density and prompt type.

The one integration touchpoint during the project itself is the rain event log. When a washout occurs, the date and approximate time should be recorded in both the project log and as a note in the weekly WordPress post. This allows rain events to be flagged as covariates in the sensor data analysis — a spike in dwell time immediately after a washout may reflect curiosity about the cleared surface rather than the prompt content.

| Dataset | Role |
|---------|------|
| **Sensor data** | Primary quantitative dataset. Covers Phase 0 through post-Week 8. Unit of analysis: dwell-time per pedestrian pass, aggregated by day and week. Key comparison: Phase 0 baseline vs. intervention weeks. |
| **Photo archive** | Primary qualitative dataset. Weekly posts on sidewalkcircus.org. Coded by: chalk density, prompt type, evidence of social connection (ribbons, responses). Key comparison: visual richness over time vs. dwell-time trend. |
| **Rain event log** | Covariate dataset. Maintained in project log and WordPress posts. Used to flag anomalous dwell-time spikes that may reflect washout curiosity rather than prompt engagement. |
| **Likert scale photographs** | Supplementary qualitative dataset. Weeks 6–8, photographed daily. Coded by distribution of marks on the scale (Isolated ↔ Connected). Cross-referenced against dwell-time data for the same days. |
