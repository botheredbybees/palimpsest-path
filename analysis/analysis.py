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
    Classify a single-sensor beam-break by how long the beam was blocked.

    transit_ms is the duration in milliseconds that ONE sensor beam was
    interrupted. A solo walker typically blocks the beam for 200–600 ms.
    A group blocks it for longer due to consecutive bodies crossing.
    A cyclist or jogger passes very quickly.

    Returns: "jogger", "regular_walker", or "slow_walker"
    """
    if transit_ms < 800:
        return "jogger"          # cyclist / runner — exclude from engagement analysis
    elif transit_ms <= 2500:
        return "regular_walker"
    else:
        return "slow_walker"     # probable engagement candidate


def classify_dwell(dwell_s):
    """
    Classify a matched gallery traversal by total dwell time.

    dwell_time_s = UNIT_B exit timestamp − UNIT_A entry timestamp.

    Returns: "Transit", "Pause", or "Dwell"
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
    Load all daily CSV files for one unit into a single DataFrame.

    Expects files matching: data_dir/unit_id/*_unit_id.csv
    Parses timestamps, sorts chronologically, drops rows with missing
    timestamps (from RTC failures), and converts transit_ms to int.
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
    Pair each UNIT_A 'inbound' event with the next unused UNIT_B 'outbound'
    event within window_s seconds.

    Matching is greedy and strictly forward in time: each UNIT_B event can
    only match once. We use the entry-side sensor's transit_ms for walker
    classification (it is the first beam the person crosses).

    Returns a DataFrame with one row per matched traversal.
    Unmatched UNIT_A events (no UNIT_B exit within the window) are discarded;
    they represent people who turned back or exited without passing UNIT_B.
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
    Assign a phase label to each matched event based on its entry timestamp.

    Phase 0  : before intervention_start
    Week N   : N weeks after intervention_start (1-indexed)
    Week 9+  : after post_int_start (Week 9 = first post-intervention week)
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
    Apply DBSCAN to discover natural behavioural clusters in the
    [dwell_time_s, transit_ms] space, beyond the rule-based thresholds.

    WHY DBSCAN INSTEAD OF KMeans:
    ─────────────────────────────
    KMeans has two fundamental mismatches with this data:
      1. You must specify k (number of clusters) upfront. We don't know how
         many natural behavioural groups exist.
      2. KMeans forces every point into a cluster — long-dwell outliers
         (e.g. a 20-minute conversation) would distort the centroid of the
         "Dwell" cluster rather than being flagged as unusual.

    DBSCAN requires only two parameters:
      eps        — how close two data points need to be (in standardised units)
                   to be considered "neighbours".
      min_samples — minimum number of neighbours for a point to be a
                   cluster core. Below this, points are labelled -1 (noise).

    After StandardScaler normalisation, 1 unit ≈ 1 standard deviation.
    eps = 0.5 means: two events are neighbours if they're within half a
    standard deviation of each other in both dwell_time and transit_ms.
    Raise eps (e.g. to 0.8) if you see too many noise points (-1); lower it
    (e.g. 0.3) if distinct behaviours are merging into a single cluster.

    min_samples = 5: a behavioural pattern needs at least 5 examples to be
    called a real cluster. With hundreds of passes per week this is a low bar.
    Raise to 10–15 for a stricter definition of "natural behaviour".

    Cluster label -1 = noise (outlier) — not a failure, just an unusual event.
    Cluster labels 0, 1, 2, … = distinct behavioural groups.
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
    Aggregate matched, classified traversals by project phase.

    Joggers are excluded from all calculations (per spec: exclude from
    engagement analysis). Median is used instead of mean — it is more robust
    to the long-tail outliers that extended-dwell events create.

    Returns a DataFrame with one row per phase, suitable for export and charts.
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
    """Consistent colour scheme across all charts."""
    return {
        "Phase 0":  "#888888",
        "Week 1":   "#4c72b0", "Week 2":  "#4c72b0",
        "Week 3":   "#dd8452", "Week 4":  "#dd8452", "Week 5": "#dd8452",
        "Week 6":   "#55a868", "Week 7":  "#55a868", "Week 8": "#55a868",
        "Week 9":   "#c44e52", "Week 10": "#c44e52",
    }


def plot_weekly_boxplots(df, output_dir):
    """
    Visualisation 1: Weekly box plots of dwell time.

    The grey shaded band shows the Phase 0 baseline IQR (25th–75th percentile).
    The dashed grey line shows the baseline median.
    Phases with no data are silently skipped.

    Joggers are excluded.
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
    Visualisation 2: Proportion stacked bar chart — Transit / Pause / Dwell.

    Shows how the mix of engagement depths changes across the project arc.
    Phases with no data are omitted.
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
    Visualisation 3: Daily median dwell time with rain events overlaid.

    Rain days are highlighted as vertical shaded bands. If the rain CSV
    does not exist or is empty, the chart is produced without the overlay
    and a warning is printed.

    Rain CSV format: one column named 'date' (YYYY-MM-DD). Additional
    columns (severity, notes) are allowed but ignored.
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
    Visualisation 4: Post-intervention trend — weekly median dwell time
    as a scatter plot with a linear trend line across all phases.

    Vertical dashed lines mark the start of intervention and post-intervention.
    A separate trend line is fitted for the post-intervention phase to show
    whether behaviour is reverting to baseline, holding, or continuing to rise.

    Requires at least 2 data points in the post-intervention phase for the
    post-intervention trend line; otherwise only the overall trend is drawn.
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
    Write a clean weekly_summary.csv suitable for the project report.

    Columns:
      phase, total_walkers, total_all_incl_joggers,
      median_dwell_s, median_transit_ms,
      n_transit, n_pause, n_dwell,
      pct_transit, pct_pause, pct_dwell
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
