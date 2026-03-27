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
├── docs/                             # Source and planning documents
│   ├── project-brief.md              # Full project brief and vision
│   ├── section-07-risk-matrix.md     # Risk register and ethics framework
│   ├── section-08-data-analysis.md   # Data streams and analytical framework
│   ├── section-09-evaluation.md      # Evaluation instruments (print-ready)
│   └── technical-appendix.md        # Pico W hardware and firmware spec
│
├── site/                             # WordPress page content (source of truth)
│   ├── home.md                       # Home page
│   ├── about.md                      # About the project
│   ├── participate.md                # How to get involved
│   ├── gallery.md                    # Photo archive placeholder
│   ├── privacy.md                    # Full privacy statement
│   └── contact.md                    # Contact page
│
├── signage/                          # Print-ready boardwalk signage
│   └── qr-sign.md                    # QR code sign (plain language statement)
│
├── data/                             # Sensor logs and analysis outputs
│   └── README.md                     # Data collection notes and log index
│
├── evaluation/                       # Coding sheets and evaluation tools
│   └── README.md                     # Evaluation instrument index
│
└── .github/
    └── workflows/
        └── deploy-to-wordpress.yml   # GitHub Action: push site/ to WordPress
```

---

## Deployment

Site content lives in `site/`. Each `.md` file corresponds to a WordPress page. Changes committed to `main` are automatically pushed to [sidewalkcircus.org](https://sidewalkcircus.org) via the WordPress REST API.

See [`.github/workflows/deploy-to-wordpress.yml`](.github/workflows/deploy-to-wordpress.yml) for the deployment pipeline.

### Environment variables (GitHub Secrets)

| Secret | Description |
|--------|-------------|
| `WP_BASE_URL` | `https://sidewalkcircus.org` |
| `WP_USERNAME` | WordPress admin username |
| `WP_APP_PASSWORD` | WordPress application password (from Users → Profile → Application Passwords) |

A template for local development is provided in [`.env.example`](.env.example).

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
Hardware firmware in `docs/technical-appendix.md` is released under MIT licence.
