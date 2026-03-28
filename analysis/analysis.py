# analysis.py — Palimpsest Path behavioural data pipeline
# ──────────────────────────────────────────────────────────────────────────────
# CPython 3.9+  |  requires: pandas, scikit-learn, matplotlib, numpy
#
# Usage:
#   python analysis.py
#
# Edit the USER CONFIGURATION block below before running.
# Raw CSV files live in DATA_DIR/UNIT_A/ and DATA_DIR/UNIT_B/.
# Outputs are written to OUTPUT_DIR/.
# ──────────────────────────────────────────────────────────────────────────────

import os
import glob
from pathlib import Path
from datetime import timedelta

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # headless — swap to "TkAgg" or "Qt5Agg" for interactive
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

# ── USER CONFIGURATION ────────────────────────────────────────────────────────
# Edit these paths and dates before running.

DATA_DIR    = "data/raw"           # parent of UNIT_A/ and UNIT_B/ subdirectories
UNIT_A_ID   = "UNIT_A"
UNIT_B_ID   = "UNIT_B"

# Rain event CSV: one row per rain event, must have a 'date' column (YYYY-MM-DD)
RAIN_CSV    = "data/rain-events.csv"

OUTPUT_DIR  = "data/analysis/figures"
SUMMARY_CSV = "data/processed/weekly-summary.csv"

# Matching window: max seconds allowed between a UNIT_A inbound event and the
# next UNIT_B outbound event to be counted as a single gallery traversal.
MATCH_WINDOW_S = 300   # 5 minutes

# Project phase start dates — fill these in once deployment begins.
# Phase 0 ends the evening before INTERVENTION_START.
INTERVENTION_START = "2025-06-01"   # first day of Week 1 (chalk steps appear)
POST_INT_START     = "2025-08-03"   # first day of Week 9 (post-intervention)

# Ordered list of phase labels used for chart x-axes.
# Adjust if your project has more or fewer phases.
PHASE_ORDER = [
    "Phase 0",
    "Week 1",  "Week 2",
    "Week 3",  "Week 4",  "Week 5",
    "Week 6",  "Week 7",  "Week 8",
    "Week 9",  "Week 10",
]

# ── CLASSIFICATION RULES ──────────────────────────────────────────────────────
# These thresholds come directly from the project specification (section 8.2).

def classify_walker(transit_ms):
    """
    Classify a pedestrian by single-sensor beam-break duration.

    Parameters
    ----------
    transit_ms : int
        Duration in milliseconds that the sensor beam was continuously blocked.
        A solo walker typically reads 200–600 ms; a group of people trailing
        across reads longer due to consecutive bodies; a jogger or cyclist
        reads shorter.

    Returns
    -------
    str
        ``"jogger"`` if transit_ms < 800,
        ``"regular_walker"`` if 800 ≤ transit_ms ≤ 2500,
        ``"slow_walker"`` if transit_ms > 2500.

    Notes
    -----
    Thresholds are defined in the project specification (section 8.2).
    Joggers should be excluded from all engagement analyses downstream.
    """
    if transit_ms < 800:
        return "jogger"          # cyclist / runner — exclude from engagement analysis
    elif transit_ms <= 2500:
        return "regular_walker"
    else:
        return "slow_walker"     # probable engagement candidate


def classify_dwell(dwell_s):
    """
    Classify a matched gallery traversal by total gallery dwell time.

    Parameters
    ----------
    dwell_s : float
        Elapsed seconds between the UNIT_A entry timestamp and the matched
        UNIT_B exit timestamp.

    Returns
    -------
    str
        ``"Transit"`` if dwell_s < 30,
        ``"Pause"`` if 30 ≤ dwell_s ≤ 120,
        ``"Dwell"`` if dwell_s > 120.

    Notes
    -----
    Thresholds are defined in the project specification (section 8.2).
    ``"Dwell"`` indicates probable active engagement with the artwork;
    ``"Pause"`` indicates brief curiosity; ``"Transit"`` is a straight-through
    pass with no visible engagement.
    """
    if dwell_s < 30:
        return "Transit"   # walked straight through
    elif dwell_s <= 120:
        return "Pause"     # paused briefly — noticed something
    else:
        return "Dwell"     # probable engagement with artwork


# ── DATA LOADING ──────────────────────────────────────────────────────────────

def load_unit(data_dir, unit_id):
    """
    Load all daily CSV files for one sensor unit into a single DataFrame.

    Parameters
    ----------
    data_dir : str
        Parent directory containing per-unit subdirectories (e.g.
        ``"data/raw"`` which holds ``data/raw/UNIT_A/``).
    unit_id : str
        Unit identifier matching both the subdirectory name and the filename
        suffix (e.g. ``"UNIT_A"``).  Files matching
        ``data_dir/unit_id/*_unit_id.csv`` are loaded.

    Returns
    -------
    pandas.DataFrame
        Columns: ``timestamp`` (str), ``unit_id`` (str), ``direction`` (str),
        ``beam`` (int), ``transit_ms`` (int), ``ts`` (datetime64).
        Sorted ascending by ``ts``.  Rows with blank or unparseable timestamps
        are dropped (these arise from RTC failures on the sensor node).

    Raises
    ------
    FileNotFoundError
        If no CSV files are found matching the expected glob pattern.
    ValueError
        If files are found but all fail to parse.
    """
    pattern = os.path.join(data_dir, unit_id, f"*_{unit_id}.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"No CSV files found matching: {pattern}\n"
            f"Check DATA_DIR and that SD card data has been copied to {data_dir}/{unit_id}/"
        )
    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, dtype={"unit_id": str, "direction": str, "beam": int})
            frames.append(df)
        except Exception as e:
            print(f"  Warning: could not read {f}: {e}")
    if not frames:
        raise ValueError(f"All files for {unit_id} were unreadable.")

    combined = pd.concat(frames, ignore_index=True)
    # Drop rows with blank timestamps (RTC failure on the node)
    combined = combined[combined["timestamp"].notna() & (combined["timestamp"] != "")]
    combined["ts"] = pd.to_datetime(combined["timestamp"], errors="coerce")
    combined = combined.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    combined["transit_ms"] = pd.to_numeric(combined["transit_ms"], errors="coerce").fillna(0).astype(int)
    return combined


# ── EVENT MATCHING ────────────────────────────────────────────────────────────

def match_events(unit_a, unit_b, window_s=300):
    """
    Pair UNIT_A inbound events with the next available UNIT_B outbound event.

    Matching is greedy and strictly forward in time: for each UNIT_A
    ``"inbound"`` event, the earliest unused UNIT_B ``"outbound"`` event
    within ``window_s`` seconds is selected.  Each UNIT_B event can match at
    most once.  UNIT_A events with no eligible exit are silently discarded
    (they represent people who turned back or exited a different way).

    Parameters
    ----------
    unit_a : pandas.DataFrame
        Raw events from UNIT_A (entry end).  Must contain columns ``ts``
        (datetime64), ``direction`` (str), ``beam`` (int), ``transit_ms``
        (int).
    unit_b : pandas.DataFrame
        Raw events from UNIT_B (exit end).  Same schema as ``unit_a``.
    window_s : int, optional
        Maximum seconds between entry and exit timestamps to be considered a
        single gallery traversal.  Default is 300 (5 minutes).

    Returns
    -------
    pandas.DataFrame
        One row per matched traversal with columns: ``entry_ts``,
        ``exit_ts``, ``dwell_time_s``, ``transit_ms`` (from the UNIT_A entry
        sensor), ``entry_beam``, ``exit_beam``, ``date``, ``walker_type``,
        ``dwell_category``.

    Raises
    ------
    ValueError
        If no matched traversals are found.  Likely causes: direction labels
        are wrong, sensor orientation is reversed, or the matching window is
        too narrow for the gallery length.

    Notes
    -----
    ``transit_ms`` in the output is taken from the UNIT_A entry sensor, not
    UNIT_B, because it reflects the speed at which the person entered before
    any dwell occurred.
    """
    a_in  = unit_a[unit_a["direction"] == "inbound"].copy().reset_index(drop=True)
    b_out = unit_b[unit_b["direction"] == "outbound"].copy().reset_index(drop=True)

    matched  = []
    used_b   = set()

    for _, row_a in a_in.iterrows():
        t_entry = row_a["ts"]
        t_max   = t_entry + pd.Timedelta(seconds=window_s)

        candidates = b_out[
            (b_out["ts"] >= t_entry) &
            (b_out["ts"] <= t_max) &
            (~b_out.index.isin(used_b))
        ]
        if candidates.empty:
            continue

        best = candidates.iloc[0]   # earliest eligible exit
        dwell_s = (best["ts"] - t_entry).total_seconds()
        matched.append({
            "entry_ts":    t_entry,
            "exit_ts":     best["ts"],
            "dwell_time_s": dwell_s,
            "transit_ms":  row_a["transit_ms"],  # entry sensor duration
            "entry_beam":  row_a["beam"],
            "exit_beam":   best["beam"],
            "date":        t_entry.date(),
        })
        used_b.add(best.name)

    if not matched:
        raise ValueError(
            "No matched events found. Check that:\n"
            "  1. UNIT_A direction='inbound' and UNIT_B direction='outbound' rows exist\n"
            "  2. INTERVENTION_START date aligns with your data\n"
            "  3. SENSOR_1_PIN is the outer sensor on both units (see config.py)"
        )

    df = pd.DataFrame(matched)
    df["walker_type"]     = df["transit_ms"].apply(classify_walker)
    df["dwell_category"]  = df["dwell_time_s"].apply(classify_dwell)
    return df


# ── PHASE LABELLING ───────────────────────────────────────────────────────────

def add_phase(df, intervention_start, post_int_start):
    """
    Assign a project phase label to each matched traversal.

    Parameters
    ----------
    df : pandas.DataFrame
        Matched traversals with an ``entry_ts`` column (datetime64).
    intervention_start : str
        ISO date string (``"YYYY-MM-DD"``) for the first day of Week 1.
        All dates strictly before this are labelled ``"Phase 0"``.
    post_int_start : str
        ISO date string for the first day of the post-intervention period
        (Week 9).

    Returns
    -------
    pandas.DataFrame
        Input DataFrame with an added ``phase`` column of ordered
        ``pandas.Categorical`` dtype, using ``PHASE_ORDER`` as the category
        list.  The ordered categorical ensures correct x-axis sorting in
        matplotlib charts without manual tick manipulation.

    Notes
    -----
    Week numbers are computed as ``(date - intervention_start).days // 7 + 1``,
    so days 0–6 → Week 1, days 7–13 → Week 2, and so on.  Post-intervention
    weeks continue from ``post_int_start`` starting at 9.
    """
    t_int  = pd.Timestamp(intervention_start).date()
    t_post = pd.Timestamp(post_int_start).date()

    def label(entry_ts):
        d = entry_ts.date()
        if d < t_int:
            return "Phase 0"
        if d >= t_post:
            week_n = (d - t_post).days // 7 + 9
            return f"Week {week_n}"
        week_n = (d - t_int).days // 7 + 1
        return f"Week {week_n}"

    df["phase"] = df["entry_ts"].apply(label)
    # Ordered categorical for correct chart axis ordering
    df["phase"] = pd.Categorical(df["phase"], categories=PHASE_ORDER, ordered=True)
    return df


# ── CLUSTERING ────────────────────────────────────────────────────────────────

def run_clustering(df):
    """
    Discover natural behavioural clusters using DBSCAN on dwell and transit data.

    Applies DBSCAN to the two-dimensional space of ``[dwell_time_s,
    transit_ms]`` after StandardScaler normalisation.  Joggers are excluded
    before clustering because they are not engagement candidates.

    Parameters
    ----------
    df : pandas.DataFrame
        Matched traversals with columns ``walker_type``, ``dwell_time_s``,
        ``transit_ms``, and ``entry_ts``.

    Returns
    -------
    df : pandas.DataFrame
        Input DataFrame with an added ``cluster`` column (int).
        ``-1`` indicates a noise point (outlier); ``0, 1, 2, …`` are cluster
        labels.  Joggers receive ``-1`` via left-join fill.
    n_clusters : int
        Number of clusters found, excluding the noise label ``-1``.

    Notes
    -----
    **Why DBSCAN instead of KMeans:**

    KMeans requires the number of clusters ``k`` to be specified upfront; we
    do not know how many natural behavioural groups exist.  KMeans also forces
    every observation into a cluster, so extended-dwell outliers (e.g. a
    20-minute conversation) distort the centroid of the ``"Dwell"`` cluster
    rather than being flagged as unusual.  DBSCAN finds clusters of arbitrary
    shape and density and labels genuine outliers as noise (``-1``).

    **Parameter guidance (plain language):**

    ``eps = 0.5`` — after StandardScaler normalisation, 1 unit ≈ 1 standard
    deviation.  Two passes are "neighbours" if they are within 0.5 standard
    deviations of each other in *both* dwell time and beam-break duration.
    Raise to 0.8 if too many noise points appear; lower to 0.3 if separate
    behavioural styles are merging into one cluster.

    ``min_samples = 5`` — a pattern needs at least 5 similar observations to
    be counted as a real cluster.  Raise to 10–15 for a stricter definition
    once the dataset grows beyond several hundred matched passes.

    Cluster label ``-1`` = noise/outlier — not a failure, just an unusual
    event that does not fit any dense behavioural group.
    """
    # Exclude joggers from clustering — they're not engagement candidates
    walkers = df[df["walker_type"] != "jogger"].copy()

    features = walkers[["dwell_time_s", "transit_ms"]].values

    # StandardScaler: centres each feature at 0 with std=1.
    # Essential because dwell_time_s (0–600 s) and transit_ms (0–30 000 ms)
    # are on completely different scales; without this, transit_ms would
    # dominate the distance calculation and dwell_time would be ignored.
    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    db = DBSCAN(
        eps=0.5,           # neighbourhood radius in standardised units (see above)
        min_samples=5,     # minimum cluster size (see above)
    )
    walkers["cluster"] = db.fit_predict(X)

    n_clusters = len(set(walkers["cluster"])) - (1 if -1 in walkers["cluster"].values else 0)
    n_noise    = (walkers["cluster"] == -1).sum()
    print(f"  DBSCAN: {n_clusters} cluster(s) found, {n_noise} noise point(s)")

    # Report cluster centres in original units for interpretability
    for label in sorted(walkers["cluster"].unique()):
        if label == -1:
            continue
        c = walkers[walkers["cluster"] == label]
        print(
            f"  Cluster {label}: n={len(c)}, "
            f"median dwell={c['dwell_time_s'].median():.0f} s, "
            f"median transit={c['transit_ms'].median():.0f} ms"
        )

    df = df.merge(walkers[["entry_ts", "cluster"]], on="entry_ts", how="left")
    df["cluster"] = df["cluster"].fillna(-1).astype(int)
    return df, n_clusters


# ── WEEKLY AGGREGATION ────────────────────────────────────────────────────────

def aggregate_weekly(df):
    """
    Aggregate matched traversals by project phase for reporting.

    Parameters
    ----------
    df : pandas.DataFrame
        Matched, classified traversals with columns ``phase`` (ordered
        Categorical), ``walker_type``, ``dwell_category``, ``dwell_time_s``,
        and ``transit_ms``.

    Returns
    -------
    pandas.DataFrame
        One row per phase in ``PHASE_ORDER`` (phases with no data produce
        NaN rows rather than being omitted, preserving chart alignment).
        Columns: ``phase``, ``total_walkers``, ``total_all_incl_joggers``,
        ``median_dwell_s``, ``median_transit_ms``, ``n_transit``,
        ``n_pause``, ``n_dwell``, ``pct_transit``, ``pct_pause``,
        ``pct_dwell``.

    Notes
    -----
    Joggers are excluded from all aggregations per the project specification.
    Median is used in preference to mean because the dwell-time distribution
    has a long right tail; occasional very long dwells would inflate the mean
    disproportionately and obscure the typical walker experience.
    """
    walkers = df[df["walker_type"] != "jogger"].copy()

    total_all    = df.groupby("phase", observed=False).size().rename("total_all_incl_joggers")
    total_walkers = walkers.groupby("phase", observed=False).size().rename("total_walkers")

    agg = walkers.groupby("phase", observed=False).agg(
        median_dwell_s   =("dwell_time_s", "median"),
        median_transit_ms=("transit_ms",   "median"),
        n_transit        =("dwell_category", lambda x: (x == "Transit").sum()),
        n_pause          =("dwell_category", lambda x: (x == "Pause").sum()),
        n_dwell          =("dwell_category", lambda x: (x == "Dwell").sum()),
    ).join(total_walkers).join(total_all).reset_index()

    agg["total_walkers"] = agg["total_walkers"].fillna(0).astype(int)
    total = (agg["n_transit"] + agg["n_pause"] + agg["n_dwell"]).replace(0, np.nan)
    agg["pct_transit"] = agg["n_transit"] / total * 100
    agg["pct_pause"]   = agg["n_pause"]   / total * 100
    agg["pct_dwell"]   = agg["n_dwell"]   / total * 100
    return agg


# ── VISUALISATIONS ────────────────────────────────────────────────────────────

def _phase_colours():
    """
    Return the project's consistent phase-to-hex-colour mapping.

    Returns
    -------
    dict
        Keys are phase label strings (e.g. ``"Phase 0"``, ``"Week 1"``);
        values are matplotlib-compatible hex colour strings.  Phases within
        the same project stratum share a colour: grey for baseline, blue for
        intervention-lite, orange for prompt escalation, green for peak
        intervention, red for post-intervention.
    """
    return {
        "Phase 0":  "#888888",
        "Week 1":   "#4c72b0", "Week 2":  "#4c72b0",
        "Week 3":   "#dd8452", "Week 4":  "#dd8452", "Week 5": "#dd8452",
        "Week 6":   "#55a868", "Week 7":  "#55a868", "Week 8": "#55a868",
        "Week 9":   "#c44e52", "Week 10": "#c44e52",
    }


def plot_weekly_boxplots(df, output_dir):
    """
    Save weekly dwell-time box plots with a Phase 0 baseline reference band.

    One box is drawn per phase that contains walker data.  A grey shaded band
    spans the Phase 0 interquartile range (Q1–Q3) and a dashed grey line
    marks the Phase 0 median, providing a visual baseline for comparison
    across all intervention phases.

    Parameters
    ----------
    df : pandas.DataFrame
        Matched traversals with columns ``phase`` (ordered Categorical),
        ``dwell_time_s``, and ``walker_type``.
    output_dir : str
        Directory path for the output PNG.  Must already exist.

    Returns
    -------
    None
        Writes ``01_weekly_boxplots.png`` to ``output_dir`` at 150 dpi.

    Notes
    -----
    Joggers (``walker_type == "jogger"``) are excluded before plotting.
    Phases present in ``PHASE_ORDER`` but absent from the data are silently
    skipped so that the chart width scales to available data.
    """
    walkers = df[df["walker_type"] != "jogger"]
    phases_present = [p for p in PHASE_ORDER if p in walkers["phase"].cat.categories
                      and walkers[walkers["phase"] == p].shape[0] > 0]
    data = [walkers[walkers["phase"] == p]["dwell_time_s"].values for p in phases_present]

    fig, ax = plt.subplots(figsize=(13, 6))

    # Baseline reference band
    baseline = walkers[walkers["phase"] == "Phase 0"]["dwell_time_s"]
    if len(baseline) > 0:
        q1, q3   = baseline.quantile(0.25), baseline.quantile(0.75)
        med_base = baseline.median()
        ax.axhspan(q1, q3, alpha=0.15, color="#888888", label=f"Baseline IQR ({q1:.0f}–{q3:.0f} s)")
        ax.axhline(med_base, color="#888888", linestyle="--", linewidth=1.2,
                   label=f"Baseline median ({med_base:.0f} s)")

    bp = ax.boxplot(
        data,
        labels=phases_present,
        patch_artist=True,
        medianprops=dict(color="black", linewidth=2),
        flierprops=dict(marker=".", markersize=3, alpha=0.4),
        whiskerprops=dict(linewidth=1),
        capprops=dict(linewidth=1),
    )
    colours = _phase_colours()
    for patch, phase in zip(bp["boxes"], phases_present):
        patch.set_facecolor(colours.get(phase, "#aaaaaa"))
        patch.set_alpha(0.7)

    ax.set_title("Palimpsest Path — Dwell Time by Project Phase\n(walkers only; joggers excluded)", pad=12)
    ax.set_xlabel("Project Phase")
    ax.set_ylabel("Dwell Time (seconds)")
    ax.legend(loc="upper left", fontsize=8)
    ax.tick_params(axis="x", rotation=30)
    plt.tight_layout()
    path = os.path.join(output_dir, "01_weekly_boxplots.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_proportion_bars(weekly_df, output_dir):
    """
    Save a stacked bar chart of Transit / Pause / Dwell proportions by phase.

    Each bar represents one project phase and is divided into three segments
    showing the percentage of walker passes classified as Transit, Pause, and
    Dwell.  The total walker count (``n``) is annotated above each bar.

    Parameters
    ----------
    weekly_df : pandas.DataFrame
        Output of ``aggregate_weekly()``.  Must contain columns ``phase``,
        ``total_walkers``, ``pct_transit``, ``pct_pause``, ``pct_dwell``.
    output_dir : str
        Directory path for the output PNG.  Must already exist.

    Returns
    -------
    None
        Writes ``02_proportion_bars.png`` to ``output_dir`` at 150 dpi.
        If no phases have walker data, a warning is printed and no file
        is written.
    """
    present = weekly_df[weekly_df["total_walkers"] > 0].copy()
    if present.empty:
        print("  Warning: no walker data for proportion chart — skipping.")
        return

    fig, ax = plt.subplots(figsize=(13, 5))
    x     = range(len(present))
    b_p   = present["pct_transit"].fillna(0).values
    b_d   = (present["pct_transit"] + present["pct_pause"]).fillna(0).values

    ax.bar(x, present["pct_transit"].fillna(0), label="Transit (<30 s)",  color="#4c72b0", alpha=0.85)
    ax.bar(x, present["pct_pause"].fillna(0),   bottom=b_p,               label="Pause (30–120 s)", color="#dd8452", alpha=0.85)
    ax.bar(x, present["pct_dwell"].fillna(0),   bottom=b_d,               label="Dwell (>120 s)",  color="#55a868", alpha=0.85)

    ax.set_xticks(list(x))
    ax.set_xticklabels(present["phase"].values, rotation=30, ha="right")
    ax.set_ylabel("Proportion of passes (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Palimpsest Path — Engagement Depth by Project Phase\n(walkers only)", pad=12)
    ax.legend(loc="upper right", fontsize=8)

    # Annotate each bar with total walker count
    for i, (_, row) in enumerate(present.iterrows()):
        ax.text(i, 102, f"n={int(row['total_walkers'])}", ha="center", va="bottom", fontsize=7, color="#444")

    plt.tight_layout()
    path = os.path.join(output_dir, "02_proportion_bars.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_rain_overlay(df, rain_csv_path, output_dir):
    """
    Save a daily median dwell-time line chart with rain events highlighted.

    Each rain event date is rendered as a light-blue vertical band spanning
    that calendar day.  Dotted vertical lines mark the intervention and
    post-intervention start dates defined in the module-level configuration.

    Parameters
    ----------
    df : pandas.DataFrame
        Matched traversals with columns ``entry_ts`` (datetime64),
        ``dwell_time_s``, and ``walker_type``.
    rain_csv_path : str
        Path to a CSV file with at minimum a ``date`` column
        (``YYYY-MM-DD`` format).  Additional columns (e.g. ``severity``,
        ``notes``) are ignored.  If the file does not exist the chart is
        produced without the rain overlay and an info message is printed.
    output_dir : str
        Directory path for the output PNG.  Must already exist.

    Returns
    -------
    None
        Writes ``03_rain_overlay.png`` to ``output_dir`` at 150 dpi.

    Notes
    -----
    Joggers are excluded before computing daily medians.
    Rain events are intentionally retained in the chart rather than excluded:
    they are a documented design feature of the project (the palimpsest
    effect) and their presence in the data is meaningful for interpretation.
    """
    walkers = df[df["walker_type"] != "jogger"].copy()
    walkers["date"] = walkers["entry_ts"].dt.date
    daily  = walkers.groupby("date")["dwell_time_s"].median().reset_index()
    daily["date"] = pd.to_datetime(daily["date"])

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(daily["date"], daily["dwell_time_s"],
            color="#4c72b0", linewidth=1.5, marker="o", markersize=3, label="Daily median dwell")

    # Rain event overlay
    rain_dates = []
    if os.path.exists(rain_csv_path):
        try:
            rain_df = pd.read_csv(rain_csv_path, parse_dates=["date"])
            rain_dates = rain_df["date"].dt.date.tolist()
        except Exception as e:
            print(f"  Warning: could not load rain events from {rain_csv_path}: {e}")
    else:
        print(f"  Info: rain CSV not found at {rain_csv_path} — no overlay applied.")

    patched = False
    for rd in rain_dates:
        ax.axvspan(
            pd.Timestamp(rd),
            pd.Timestamp(rd) + pd.Timedelta(days=1),
            alpha=0.25, color="#aec6e8", zorder=0,
        )
        patched = True

    # Intervention boundary lines
    ax.axvline(pd.Timestamp(INTERVENTION_START), color="green",  linestyle=":", linewidth=1.5, label="Intervention start")
    ax.axvline(pd.Timestamp(POST_INT_START),      color="orange", linestyle=":", linewidth=1.5, label="Post-intervention start")

    handles, labels = ax.get_legend_handles_labels()
    if patched:
        handles.append(mpatches.Patch(color="#aec6e8", alpha=0.5, label="Rain event"))
    ax.legend(handles=handles + ([mpatches.Patch(color="#aec6e8", alpha=0.5, label="Rain event")] if patched and "Rain event" not in labels else []),
              fontsize=8, loc="upper left")

    ax.set_title("Palimpsest Path — Daily Median Dwell Time with Rain Events\n(walkers only)", pad=12)
    ax.set_xlabel("Date")
    ax.set_ylabel("Median Dwell Time (seconds)")
    fig.autofmt_xdate()
    plt.tight_layout()
    path = os.path.join(output_dir, "03_rain_overlay.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_post_intervention_trend(weekly_df, output_dir):
    """
    Save a scatter-and-trend-line chart of weekly median dwell time over time.

    Plots the weekly median dwell time for each phase as a scatter point
    (coloured by project stratum) with two superimposed trend lines: an
    overall linear fit across all phases, and a separate fit for the
    post-intervention period (Weeks 9+).  The post-intervention slope
    indicates whether behaviour is persisting, reverting to baseline, or
    continuing to change after the chalk installation is removed.

    Parameters
    ----------
    weekly_df : pandas.DataFrame
        Output of ``aggregate_weekly()``.  Must contain columns ``phase``,
        ``total_walkers``, and ``median_dwell_s``.
    output_dir : str
        Directory path for the output PNG.  Must already exist.

    Returns
    -------
    None
        Writes ``04_post_intervention_trend.png`` to ``output_dir`` at 150 dpi.
        If no phases have walker data, a warning is printed and no file is
        written.  The post-intervention trend line is omitted silently if
        fewer than 2 post-intervention data points are available.

    Notes
    -----
    Trend lines are fitted with ``numpy.polyfit`` (degree 1, least-squares
    linear regression).  No confidence intervals are shown; the dataset is
    too small for reliable interval estimation.  The slope is labelled in
    seconds per phase for plain-language readability.
    """
    present = weekly_df[weekly_df["total_walkers"] > 0].copy()
    if present.empty:
        print("  Warning: no data for trend plot — skipping.")
        return

    # Numeric x-axis (phase index in PHASE_ORDER)
    present["phase_idx"] = present["phase"].apply(
        lambda p: PHASE_ORDER.index(p) if p in PHASE_ORDER else -1
    )
    present = present[present["phase_idx"] >= 0]

    colours = _phase_colours()
    fig, ax = plt.subplots(figsize=(11, 6))

    # Scatter points coloured by phase
    for _, row in present.iterrows():
        ax.scatter(
            row["phase_idx"], row["median_dwell_s"],
            color=colours.get(row["phase"], "#aaa"),
            s=80, zorder=5,
        )
        ax.annotate(
            f"{row['median_dwell_s']:.0f} s",
            (row["phase_idx"], row["median_dwell_s"]),
            textcoords="offset points", xytext=(0, 8), fontsize=7, ha="center",
        )

    # Overall linear trend line
    x_all = present["phase_idx"].values
    y_all = present["median_dwell_s"].values
    if len(x_all) >= 2:
        z    = np.polyfit(x_all, y_all, 1)
        p    = np.poly1d(z)
        x_fit = np.linspace(x_all.min(), x_all.max(), 200)
        ax.plot(x_fit, p(x_fit), "k--", linewidth=1.2, alpha=0.5,
                label=f"Overall trend ({z[0]:+.1f} s/phase)")

    # Post-intervention trend line (phases 9+)
    post = present[present["phase_idx"] >= PHASE_ORDER.index("Week 9")]
    if len(post) >= 2:
        z_post = np.polyfit(post["phase_idx"].values, post["median_dwell_s"].values, 1)
        p_post = np.poly1d(z_post)
        x_post = np.linspace(post["phase_idx"].min(), post["phase_idx"].max(), 200)
        direction = "↑ persisting" if z_post[0] > 0 else "↓ reverting to baseline"
        ax.plot(x_post, p_post(x_post), color="#c44e52", linewidth=2,
                label=f"Post-intervention trend {direction}")

    # Phase boundary lines
    int_idx  = PHASE_ORDER.index("Week 1") if "Week 1" in PHASE_ORDER else None
    post_idx = PHASE_ORDER.index("Week 9") if "Week 9" in PHASE_ORDER else None
    if int_idx is not None:
        ax.axvline(int_idx - 0.5, color="green",  linestyle=":", linewidth=1.5, label="Intervention start")
    if post_idx is not None:
        ax.axvline(post_idx - 0.5, color="orange", linestyle=":", linewidth=1.5, label="Post-intervention start")

    ax.set_xticks(range(len(PHASE_ORDER)))
    ax.set_xticklabels(PHASE_ORDER, rotation=30, ha="right")
    ax.set_title("Palimpsest Path — Weekly Median Dwell Time: Trend Analysis\n(walkers only)", pad=12)
    ax.set_xlabel("Project Phase")
    ax.set_ylabel("Median Dwell Time (seconds)")
    ax.legend(fontsize=8)
    plt.tight_layout()
    path = os.path.join(output_dir, "04_post_intervention_trend.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


# ── SUMMARY EXPORT ────────────────────────────────────────────────────────────

def export_summary(weekly_df, df, output_path):
    """
    Write the weekly aggregation table to a CSV for use in the project report.

    Parameters
    ----------
    weekly_df : pandas.DataFrame
        Output of ``aggregate_weekly()``.
    df : pandas.DataFrame
        Full matched traversals DataFrame.  Currently unused; retained in the
        signature for future per-event export extensions.
    output_path : str
        Full file path for the output CSV (e.g.
        ``"data/processed/weekly-summary.csv"``).  Parent directories are
        created automatically if they do not exist.

    Returns
    -------
    None
        Writes a CSV with columns: ``phase``, ``total_walkers``,
        ``total_all_incl_joggers``, ``median_dwell_s``, ``median_transit_ms``,
        ``n_transit``, ``n_pause``, ``n_dwell``, ``pct_transit``,
        ``pct_pause``, ``pct_dwell``.  Float columns are rounded to 1 decimal
        place for readability.
    """
    out = weekly_df[[
        "phase",
        "total_walkers", "total_all_incl_joggers",
        "median_dwell_s", "median_transit_ms",
        "n_transit", "n_pause", "n_dwell",
        "pct_transit", "pct_pause", "pct_dwell",
    ]].copy()

    # Round floats for readability
    for col in ["median_dwell_s", "median_transit_ms", "pct_transit", "pct_pause", "pct_dwell"]:
        out[col] = out[col].round(1)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"  Saved summary: {output_path}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    """
    Run the full Palimpsest Path analysis pipeline end-to-end.

    Executes the following steps in order:

    1. Load raw CSV files for UNIT_A and UNIT_B from ``DATA_DIR``.
    2. Match UNIT_A inbound events to UNIT_B outbound events within
       ``MATCH_WINDOW_S`` seconds to compute ``dwell_time_s``.
    3. Label each matched traversal with a project phase.
    4. Run DBSCAN clustering on walker (non-jogger) traversals.
    5. Aggregate statistics by phase.
    6. Produce four PNG visualisations and export ``weekly-summary.csv``.

    Returns
    -------
    None
        All outputs are written to ``OUTPUT_DIR`` and ``SUMMARY_CSV``.
        Progress is reported to stdout.

    Notes
    -----
    Edit the ``USER CONFIGURATION`` block at the top of this module before
    running.  At minimum, set ``INTERVENTION_START`` and ``POST_INT_START``
    to match your deployment dates, and verify ``DATA_DIR`` points to the
    directory containing the ``UNIT_A/`` and ``UNIT_B/`` subdirectories.
    """
    print("Palimpsest Path — Analysis Pipeline")
    print("=" * 50)

    # Ensure output directories exist
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)

    # 1. Load raw data
    print("\n[1/6] Loading sensor data...")
    unit_a = load_unit(DATA_DIR, UNIT_A_ID)
    unit_b = load_unit(DATA_DIR, UNIT_B_ID)
    print(f"  UNIT_A: {len(unit_a):,} events")
    print(f"  UNIT_B: {len(unit_b):,} events")

    # 2. Match entry/exit events
    print("\n[2/6] Matching traversals (window: {MATCH_WINDOW_S} s)...".format(MATCH_WINDOW_S=MATCH_WINDOW_S))
    matched = match_events(unit_a, unit_b, window_s=MATCH_WINDOW_S)
    print(f"  {len(matched):,} matched traversals")
    n_joggers = (matched["walker_type"] == "jogger").sum()
    print(f"  Walker breakdown: {(matched['walker_type']=='jogger').sum()} joggers, "
          f"{(matched['walker_type']=='regular_walker').sum()} regular walkers, "
          f"{(matched['walker_type']=='slow_walker').sum()} slow walkers")

    # 3. Phase labelling
    print("\n[3/6] Labelling project phases...")
    matched = add_phase(matched, INTERVENTION_START, POST_INT_START)

    # 4. Clustering
    print("\n[4/6] Running DBSCAN clustering (walkers only)...")
    matched, n_clusters = run_clustering(matched)

    # 5. Weekly aggregation
    print("\n[5/6] Aggregating by phase...")
    weekly = aggregate_weekly(matched)

    # 6. Visualisations and export
    print(f"\n[6/6] Generating charts → {OUTPUT_DIR}")
    plot_weekly_boxplots(matched, OUTPUT_DIR)
    plot_proportion_bars(weekly, OUTPUT_DIR)
    plot_rain_overlay(matched, RAIN_CSV, OUTPUT_DIR)
    plot_post_intervention_trend(weekly, OUTPUT_DIR)
    export_summary(weekly, matched, SUMMARY_CSV)

    print("\nDone.")
    print(f"  Charts:  {OUTPUT_DIR}/")
    print(f"  Summary: {SUMMARY_CSV}")


if __name__ == "__main__":
    main()
