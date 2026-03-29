# The Palimpsest Path

**A community chalk art project on the Cygnet Boardwalk, Tasmania**

Project Lead: Peter Shanks ([@botheredbybees](https://github.com/botheredbybees))
Academic context: FXA301 Arts in the Community, University of Tasmania
Public site: [sidewalkcircus.org](https://sidewalkcircus.org)

---

## What is the Palimpsest Path?

The Palimpsest Path transforms a 100-metre section of the Cygnet Boardwalk from a transient thoroughfare into a therapeutic landscape. Using non-toxic calcium carbonate chalk on the boardwalk's vertical bannisters and walkway surfaces, the project invites regular walkers to slow down, contribute to an evolving shared narrative, and connect with each other — asynchronously, anonymously, and without obligation.

The project takes its name from the palimpsest — a manuscript surface that has been written on, partially erased, and written on again, with traces of every previous layer still visible. Tasmanian rain acts as the natural reset mechanism: contributions wash away, the surface clears, and new stories begin on top of old ones. This cycle reduces the aesthetic anxiety that often inhibits participation in public art and encourages high-frequency, low-stakes engagement.

The core intervention mechanics begin with chalked "dance step" trails — outlines of shoes arranged in old-time dance sequences — which invite walkers to pause, rehearse the steps, and gradually take up the chalk themselves. Over eight weeks, the prompt structure deepens from sensory observation to personal narrative to collective imagining.

---

## Repository Structure

```
palimpsest-path/
│
├── README.md                         # This file
│
├── firmware/                         # MicroPython sensor node firmware
│   ├── README.md                     # Deployment guide, wiring, troubleshooting
│   ├── config.py                     # All tunable constants (pins, thresholds, UNIT_ID)
│   ├── main.py                       # Firmware entry point — runs automatically on boot
│   └── test_sensors.py               # Pre-deployment hardware self-test (run via REPL)
│
├── analysis/                         # CPython data analysis pipeline
│   ├── analysis.py                   # Full pipeline: load → match → classify → cluster → plot
│   └── tests/                        # pytest unit tests
│       └── test_analysis.py          # Edge-case tests for matching and classification
│
├── docs/                             # Source and planning documents
│   ├── project-brief.md              # Full project brief and vision
│   ├── section-07-risk-matrix.md     # Risk register and ethics framework
│   ├── section-08-data-analysis.md   # Data streams and analytical framework
│   ├── section-09-evaluation.md      # Evaluation instruments (print-ready)
│   └── technical-appendix.md        # Hardware wiring diagrams and BOM
│
├── site/                             # WordPress page content (source of truth)
│   ├── home.md                       # Home page
│   ├── about.md                      # About the project
│   ├── participate.md                # How to get involved
│   ├── gallery.md                    # Photo archive and community stories
│   ├── privacy.md                    # Full privacy statement
│   ├── contact.md                    # Contact page (Contact Form 7)
│   └── ideas.md                      # Ideas & artwork suggestions (Contact Form 7)
│
├── upload.py                         # Local WordPress deployer — reads site/*.md and pushes via REST API
│
├── signage/                          # Print-ready boardwalk signage
│   └── qr-sign.md                    # QR code sign (plain language statement)
│
├── data/                             # Sensor logs and analysis outputs (raw data gitignored)
│   └── README.md                     # Data collection protocol and phase log
│
├── evaluation/                       # Coding sheets and evaluation tools
│   └── README.md                     # Evaluation instrument index
│
└── .github/
    └── workflows/
        └── deploy-to-wordpress.yml   # GitHub Action: push site/ to WordPress
```

---

## Sensor Firmware

Two identical Raspberry Pi Pico (RP2040) units sit at the entry and exit ends of the 100 m boardwalk gallery. Each monitors two E18-D80NK infrared proximity sensors, timestamps beam-break events via a DS3231 RTC, and logs rows to a daily CSV on a SPI micro-SD card. No wireless communication is used at any point.

| File | Purpose |
|------|---------|
| `firmware/config.py` | All tunable constants — the only file that differs between the two units (`UNIT_ID = "UNIT_A"` vs `"UNIT_B"`) |
| `firmware/main.py` | Interrupt-driven firmware with `machine.lightsleep()` between events to minimise battery draw. Logs fields: `timestamp`, `unit_id`, `direction`, `beam`, `transit_ms` |
| `firmware/test_sensors.py` | Interactive self-test script — run via USB REPL before sealing each unit. Tests DS3231 clock, both IR sensors, and SD card read/write |

See [`firmware/README.md`](firmware/README.md) for wiring, the RTC clock-setting snippet, deployment steps, and LED error codes.

---

## Data Analysis

The CPython pipeline in `analysis/analysis.py` processes the raw CSV logs after each SD card retrieval.

```
data/raw/UNIT_A/*.csv  ──┐
                          ├──▶ match_events() ──▶ classify ──▶ cluster ──▶ aggregate ──▶ charts + summary CSV
data/raw/UNIT_B/*.csv  ──┘
```

| Step | What it does |
|------|-------------|
| Load | Reads all daily CSVs for both units; drops rows with blank timestamps (RTC failures) |
| Match | Pairs each UNIT_A `inbound` event with the next UNIT_B `outbound` event within a 5-minute window to compute `dwell_time_s` |
| Classify | Labels each pass by walker type (`transit_ms`: jogger / regular_walker / slow_walker) and dwell category (`dwell_time_s`: Transit / Pause / Dwell) |
| Cluster | DBSCAN on `[dwell_time_s, transit_ms]` to find natural behavioural groups beyond the rule-based thresholds |
| Aggregate | Weekly medians and proportions (walkers only; joggers excluded) |
| Output | Four PNG charts + `data/processed/weekly-summary.csv` |

**Run the pipeline:**

```bash
pip install pandas scikit-learn matplotlib numpy
python analysis/analysis.py
```

Edit the `USER CONFIGURATION` block at the top of `analysis/analysis.py` to set `DATA_DIR`, `INTERVENTION_START`, and `POST_INT_START` before the first run.

Unit tests for the matching and classification logic live in `analysis/tests/test_analysis.py` and run with `pytest analysis/`.

---

## WordPress Deployment

Site content lives in `site/`. Each `.md` file corresponds to a WordPress page and is the source of truth for that page's content, title, slug, and status.

Pages are deployed locally using `upload.py`:

```bash
python upload.py           # deploy all site/*.md files
python upload.py about.md  # deploy a single file
```

The script reads credentials from a `.env` file in the repo root. Copy `.env.example` to `.env` and fill in your values:

| Variable | Description |
|----------|-------------|
| `WP_BASE_URL` | `https://sidewalkcircus.org` |
| `WP_USERNAME` | WordPress admin username |
| `WP_APP_PASSWORD` | WordPress application password (from Users → Profile → Application Passwords) |

The script matches pages by slug. If a page with that slug exists it is updated; if not, a new page is created. Published pages take priority over drafts when resolving slug conflicts.

---

## Project Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Phase 0 | 2–3 weeks | Baseline sensor data collection, council permit, site prep |
| Weeks 1–2 | 2 weeks | Dance step trails only — silent phase |
| Weeks 3–5 | 3 weeks | Chalk stations open, progressive prompt escalation |
| Weeks 6–8 | 3 weeks | Peak intervention, community co-authorship |
| Weeks 9–10 | 2 weeks | Post-intervention — habits persistence observation |

---

## Ethics and Privacy

The project operates under a Privacy by Design framework. No cameras, no Wi-Fi monitoring, and no personal data collection of any kind. The sensor system uses infrared beam counters that record only anonymous pedestrian transit times to a local SD card.

Full details: [sidewalkcircus.org/privacy](https://sidewalkcircus.org/privacy) and [`docs/section-07-risk-matrix.md`](docs/section-07-risk-matrix.md).

---

## Licence

Project documentation and site content © Peter Shanks 2025–2026.
Sensor firmware (`firmware/`) and analysis pipeline (`analysis/`) are released under the MIT licence.
