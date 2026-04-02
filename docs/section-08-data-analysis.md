# Section 8: Data Analysis

**Baseline vs. Intervention — Three Parallel Data Streams**

---

## 8.1 Analytical Framework

The Palimpsest Path generates three parallel, independent data streams that together form a mixed-methods evaluation of the intervention's effect on community wellbeing and social connection. No single stream tells the full story; the project's analytical power comes from their triangulation.

Each stream runs from a different start point but all extend through to at least two weeks post-intervention, enabling a "habits persistence" analysis after materials are withdrawn.

| Stream | Type | Starts | Primary Question |
|--------|------|--------|-----------------|
| **Pico W Dwell Times** | Quantitative | Phase 0 (pure baseline) | Do walkers slow down and linger more during the intervention? |
| **Happiness Index** | Quantitative + Visual | Week 3 (alongside first prompt) | Do self-reported happiness levels change over the intervention arc? |
| **Photo-Narrative Archive** | Qualitative | Week 1 | What themes, connections and patterns emerge in community contributions? |

A fourth covariate dataset — the rain event log — runs throughout and is used to flag anomalous readings in all three streams. Rain events are not a confound to be eliminated; they are a design feature to be documented.

---

## 8.2 Stream 1: Pico W Dwell-Time Analysis

### Dataset A — Pico W Infrared Sensor Logs

| Parameter | Value |
|-----------|-------|
| **Format** | Timestamped CSV. One row per IR beam-break event. Fields: `timestamp`, `unit_id`, `direction`, `beam`, `transit_ms` |
| **Volume** | Estimated 50–300 events/day. ~10 weeks × 7 days = ~70 files per unit |
| **Valid days required** | Minimum 10 clean days in Phase 0 before Week 1. Total target: 60+ valid days across the full arc |
| **Covariates** | Rain event log (date and approximate time of washout events), flagged in analysis |

### Analysis Steps

**Step 1: Clean and classify raw events**

For each valid day:

1. Load CSV for UNIT_A and UNIT_B
2. Match INBOUND events at UNIT_A with OUTBOUND events at UNIT_B (within a 5-minute window)
3. Calculate `dwell_time = UNIT_B.timestamp - UNIT_A.timestamp`
4. Classify each pass:
   - `dwell < 30s` → Transit
   - `dwell 30–120s` → Pause
   - `dwell > 120s` → Dwell (probable engagement)

   *Threshold justification:* At a normal walking pace of ~1.2 m/s, the 100m gallery section takes approximately 83 seconds to traverse. Any pass recorded above ~120s has therefore demonstrably slowed or stopped — the threshold is not arbitrary but grounded in the basic kinematics of the site. The 30s lower bound distinguishes brief hesitations (glance at chalk, adjust bag) from purposeful pauses; it is set conservatively below the expected transit time to capture the full pause category without misclassifying fast walkers.

5. Classify walker type from `transit_ms`:
   - `< 800ms` → Jogger / cyclist (exclude from engagement analysis)
   - `800–2500ms` → Regular walker
   - `> 2500ms` → Slow walker / participant candidate

**Step 2: Aggregate by week and stratum**

For each week, calculate: median dwell time (walkers only), proportion of passes classified as Pause or Dwell, and total valid pedestrian count. Median is preferred over mean — it is more robust to outliers created by extended dwell events.

**Step 3: Compare strata**

| Stratum | Weeks | Comparison Purpose |
|---------|-------|--------------------|
| **Pure Baseline** | Phase 0 | Pre-intervention norm. No chalk, no signage. The cleanest counterfactual. |
| **Intervention-lite** | Weeks 1–2 | Steps only. Tests whether a visual stimulus alone produces measurable dwell change. |
| **Prompt Escalation** | Weeks 3–5 | Progressive deepening. Are longer or more personal prompts associated with longer dwell times? |
| **Peak Intervention** | Weeks 6–8 | Maximum chalk density and community co-authorship. Expected peak dwell divergence from baseline. |
| **Post-intervention** | Weeks 9–10 | Do behaviours persist after materials are withdrawn? The "habits persistence" test. |

**Step 4: Visualisation**

- Weekly box plot of dwell times: baseline vs. each intervention week. Baseline shown as reference band.
- Proportion chart: % of passes classified as Transit / Pause / Dwell per week.
- Rain event overlay: mark washout dates on all charts to assess whether post-washout curiosity spikes are visible.
- Post-intervention trend line: does the dwell-time distribution in Weeks 9–10 revert to baseline, maintain, or continue to increase?

---

## 8.3 Stream 2: The Happiness Index

The Happiness Index is the project's self-reported subjective wellbeing measure. It is a chalk bar graph drawn by participants on the top surface of the bannister rail, generating both a quantitative time-series and a rich visual archive.

### Dataset B — Happiness Index (Chalk Bar Graph)

| Parameter | Value |
|-----------|-------|
| **Format** | Daily photographs of chalk bar graph surface. Bars drawn by participants on a pre-ruled 0–10 vertical scale. |
| **Cadence** | Photographed each morning as part of the Daily Audit. Fresh graph drawn each day — wiped clean before the day's bars are drawn. |
| **Starts** | Week 3 — introduced alongside the first chalk prompt |
| **Label on boardwalk** | Simple chalk label: "Happiness" with a 0–10 scale and smile/frown indicators. No written instruction. |
| **Coding unit** | Each weekday photograph is a single observation: number of bars visible, estimated median bar height (0–10), distribution shape, any participant annotations |

### Graph Design

**Axes:** X-axis: days of the week (M T W T F), spaced ~15 cm apart. Y-axis: scale 0–10, ruled at 0, 5, and 10 minimum. Label the Y-axis: "Happiness" with a simple smile/frown indicator at top and bottom.

**Scale:** Y-axis spans the full ~18cm depth of the bannister top rail (0 at near edge, 10 at far/water edge). X-axis extends along the rail length, with days spaced ~15cm apart (~75cm total for a 5-day week). Pre-draw a sample bar in white each morning to model the behaviour.

**Reset:** Re-draw axes fresh each morning in chalk marker before the day begins. If rain washes the graph during the day: photograph the cleared surface (the blank is data), then re-draw axes for the remainder of the day if practical. Do not attempt to reconstruct bars that were washed away.

**Location:** On the top surface of the bannister rail adjacent to the primary chalk station. X-axis (days) runs along the rail length; Y-axis (happiness scale 0–10) runs across the 18cm rail depth, from near edge (0) to water edge (10). Visible from standing height when walking past.

### Analysis Steps

**Step 1: Photo coding**

For each weekday photograph, record in a spreadsheet: date and week number, number of bars visible, estimated median bar height, distribution (clustered high / mid-range / clustered low / spread), any written annotations, rain/reset flag.

**Step 2: Weekly aggregate**

For each week: median bar height across all valid weekdays, mean participant count per day, proportion of bars in each distribution band. Flag weeks with fewer than 3 valid observation days due to rain.

**Step 3: Longitudinal comparison**

- Plot median weekly happiness score across all 8 weeks as a line chart.
- Overlay on the Pico W dwell-time chart: do happiness scores and dwell times track together?
- Note weeks where the graph was reset by rain — natural before/after comparison.
- Compare early weeks (3–4) against later weeks (6–8): does median daily happiness increase as community co-authorship deepens?

> **Methodological honesty note:** The happiness index has significant self-selection bias — only walkers who choose to engage with the chalk contribute. It is not a representative sample of all boardwalk users. The Pico W sensor data provides the population-level behavioural measure; the happiness index provides the self-reported affective measure from the engaged subset. Both are valid and complementary.

---

## 8.4 Stream 3: Photo-Narrative Archive

### Dataset C — Photo-Narrative Archive (sidewalkcircus.org)

| Parameter | Value |
|-----------|-------|
| **Format** | Daily photographs of chalk surface contributions, uploaded to sidewalkcircus.org gallery |
| **Volume** | Target: 1–3 photographs per day across the 8-week intervention, supplemented by participant-submitted photos |
| **Starts** | Week 1 — first dance step photographs establish the visual baseline |
| **Coding approach** | Thematic analysis using an iterative coding framework (see Section 9) |

### Analysis Steps

**Step 1: Weekly thematic coding**

Each week's photograph set is reviewed and coded against six dimensions:

| Dimension | What to Code |
|-----------|-------------|
| **Chalk density** | Low (1–2 marks), Medium (3–10 marks), High (10+ marks) |
| **Contribution type** | Dance step addition / Narrative response / Abstract decoration / Ribbon / Happiness bar / Likert scale mark / Other |
| **Social connection evidence** | Does the contribution reference or respond to another mark? (Direct response, ribbon link, shared theme.) |
| **Emotional valence** | Positive / Neutral / Negative |
| **Prompt adherence** | Does the contribution relate to the current week's prompt, or is it independent? Independent contributions are not failures — they indicate participant agency. |
| **Rain event evidence** | Traces of partially washed contributions visible. Contributes to understanding of the layering effect. |

**Step 2: Theme identification**

After Week 4 (mid-point), review all coded photographs and identify emergent themes. These may be place-specific (repeated references to the water, local landmarks), relational (responses to other walkers' stories), or affective (emotional patterns across the arc).

**Step 3: Narrative arc analysis**

Map the evolution of the chalk surface over 8 weeks as a visual narrative: from the first traced steps through the layered, rain-reset, community-authored surface of Week 8. The photo archive should be sequenced and annotated to tell this story in the evaluation report.

---

## 8.5 Triangulation: Reading the Three Streams Together

| Combination | Interpretation |
|-------------|---------------|
| **Dwell time↑ + Happiness↑** | If weeks with higher median dwell times also show higher median happiness bar heights, this is the project's strongest finding: the intervention is associated with both behavioural engagement and subjective wellbeing. Interpret with care given self-selection bias in the happiness index. |
| **Dwell time↑ + Sparse chalk** | If dwell times increase in weeks with low chalk density, the step trail itself — rather than the narrative prompts — may be the primary driver of engagement. Useful for future replication at lower material cost. |
| **Post-washout engagement spike** | If dwell times and/or happiness scores increase in the 24–48 hours after a rain washout, this supports the palimpsest effect hypothesis: the freshly cleared surface generates heightened curiosity and participation. |
| **Post-intervention persistence** | If dwell times in Weeks 9–10 remain above Phase 0 baseline, this is evidence of habit formation — the project's highest-value finding for future policy arguments. Even a modest residual effect (e.g. 15% above baseline) would be meaningful. |
| **Prompt type vs. engagement** | Compare median dwell times across prompt types: sensory, identity, social, and collective vision. Do more personal or future-oriented prompts produce longer dwells or more happiness responses? |

---

## 8.6 Social Return on Investment (SROI)

The SROI analysis translates the project's documented outcomes into a framework that can be communicated to Council and community health stakeholders. It does not claim to produce a precise financial figure — the project scale does not warrant that precision — but it provides a structured argument for the cost-effectiveness of the intervention.

| Component | Details |
|-----------|---------|
| **Inputs (costs)** | Project budget: ~$228 AUD. Project lead time: estimated 3–4 hours/week × 10 weeks = ~35 hours at student/volunteer rate. |
| **Outputs (measurable)** | Number of pedestrian passes recorded (Pico W total count). Number of engagement events (Pause + Dwell classifications). Number of chalk contributions (photo-narrative count). Number of happiness index bars drawn. Number of QR code scans (WordPress analytics). |
| **Outcomes (inferred)** | Reduction in parallel isolation (dwell-time increase + social connection evidence in photo archive). Improved subjective wellbeing (happiness index trend). Increased sense of community (thematic analysis of narrative contributions). |
| **Proxy values** | One meaningful social interaction: ~$30 AUD (after Fancourt & Finn, 2019). One unit increase in happiness score (0–10) per participant: ~$15 AUD proxy value. These proxies should be treated as illustrative, not precise. State assumptions explicitly. |

---

## 8.7 Limitations & Methodological Honesty

The following limitations should be stated explicitly in the evaluation report. Naming them is not a weakness — it demonstrates methodological rigour and academic honesty.

- **Self-selection bias** in the happiness index: only participants who choose to engage with the chalk contribute bars. The sample is not representative of all boardwalk users.
- **No control site:** without a comparable boardwalk running simultaneously without intervention, causal claims are limited. The Pico W baseline is a within-site comparison.
- **Small sample size:** Cygnet is a small community. Daily engagement numbers may be low. Frame findings as a pilot study, not a statistically powered trial.
- **Researcher presence effect:** the daily audit means the project lead is a visible presence on the boardwalk, which may itself influence walker behaviour.
- **Weather dependency:** extended rain periods create gaps in all three datasets. Document all gaps and exclude affected days from statistical comparisons rather than interpolating.
- **Photo coding subjectivity:** thematic analysis involves interpretive judgement. Where possible, code independently on two separate occasions and note any changes.
