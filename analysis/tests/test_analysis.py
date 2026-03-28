# analysis/tests/test_analysis.py
# ──────────────────────────────────────────────────────────────────────────────
# pytest suite for the Palimpsest Path analysis pipeline.
#
# Run from the repository root:
#   pytest analysis/
#
# conftest.py (sibling file) adds analysis/ to sys.path so that
# "from analysis import ..." resolves to analysis/analysis.py.
# ──────────────────────────────────────────────────────────────────────────────

import pytest
import pandas as pd
import numpy as np

from analysis import (
    classify_walker,
    classify_dwell,
    match_events,
    add_phase,
    aggregate_weekly,
    PHASE_ORDER,
)

# ── Shared constants ──────────────────────────────────────────────────────────

# Anchor timestamp used as t=0 for relative event construction
BASE_TIME = pd.Timestamp("2025-06-15 09:00:00")

# Must match the values hard-coded in add_phase tests below
INTERVENTION_START = "2025-06-01"
POST_INT_START = "2025-08-03"


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_unit_df(event_specs):
    """
    Build a minimal sensor-event DataFrame suitable for match_events().

    Parameters
    ----------
    event_specs : list of (delta_s, direction, transit_ms)
        delta_s    – seconds after BASE_TIME
        direction  – "inbound" or "outbound"
        transit_ms – beam-break duration in milliseconds

    Returns
    -------
    pandas.DataFrame
        Columns: ts, direction, beam, transit_ms.
        Rows are sorted by ts.  An empty spec list returns an empty DataFrame
        with the correct column schema so direction-filtering still works.
    """
    if not event_specs:
        return pd.DataFrame(columns=["ts", "direction", "beam", "transit_ms"])

    rows = [
        {
            "ts": BASE_TIME + pd.Timedelta(seconds=delta_s),
            "direction": direction,
            "beam": 1,
            "transit_ms": int(transit_ms),
        }
        for delta_s, direction, transit_ms in event_specs
    ]
    return pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)


def make_phase_df(rows):
    """
    Build a classified traversal DataFrame suitable for aggregate_weekly().

    Parameters
    ----------
    rows : list of (phase_str, walker_type, dwell_category, dwell_time_s)

    Returns
    -------
    pandas.DataFrame
        phase column is an ordered Categorical using PHASE_ORDER.
    """
    records = [
        {
            "phase": phase,
            "walker_type": walker_type,
            "dwell_category": dwell_cat,
            "dwell_time_s": float(dwell_s),
            "transit_ms": 1000,
            "entry_ts": BASE_TIME,
        }
        for phase, walker_type, dwell_cat, dwell_s in rows
    ]
    df = pd.DataFrame(records)
    df["phase"] = pd.Categorical(df["phase"], categories=PHASE_ORDER, ordered=True)
    return df


# ── classify_walker ───────────────────────────────────────────────────────────

class TestClassifyWalker:
    """Boundary and range tests for the transit_ms → walker-type classifier."""

    def test_zero_is_jogger(self):
        assert classify_walker(0) == "jogger"

    def test_well_below_jogger_threshold(self):
        assert classify_walker(400) == "jogger"

    def test_just_below_regular_boundary(self):
        assert classify_walker(799) == "jogger"

    def test_at_regular_lower_boundary(self):
        # spec: 800–2500 ms → regular_walker
        assert classify_walker(800) == "regular_walker"

    def test_regular_midrange(self):
        assert classify_walker(1500) == "regular_walker"

    def test_at_regular_upper_boundary(self):
        # 2500 ms is still regular_walker (spec: 800–2500)
        assert classify_walker(2500) == "regular_walker"

    def test_just_above_regular_boundary(self):
        # spec: > 2500 ms → slow_walker
        assert classify_walker(2501) == "slow_walker"

    def test_well_above_slow_threshold(self):
        assert classify_walker(10_000) == "slow_walker"


# ── classify_dwell ────────────────────────────────────────────────────────────

class TestClassifyDwell:
    """Boundary and range tests for the dwell_time_s → dwell-category classifier."""

    def test_zero_seconds_is_transit(self):
        assert classify_dwell(0.0) == "Transit"

    def test_well_below_pause_boundary(self):
        assert classify_dwell(10.0) == "Transit"

    def test_just_below_pause_boundary(self):
        assert classify_dwell(29.9) == "Transit"

    def test_at_pause_lower_boundary(self):
        # spec: 30–120 s → Pause
        assert classify_dwell(30.0) == "Pause"

    def test_pause_midrange(self):
        assert classify_dwell(75.0) == "Pause"

    def test_at_pause_upper_boundary(self):
        # 120 s is still Pause (spec: 30–120)
        assert classify_dwell(120.0) == "Pause"

    def test_just_above_dwell_boundary(self):
        # spec: > 120 s → Dwell
        assert classify_dwell(120.1) == "Dwell"

    def test_well_above_dwell_threshold(self):
        assert classify_dwell(600.0) == "Dwell"


# ── match_events ──────────────────────────────────────────────────────────────

class TestMatchEvents:
    """
    Edge-case tests for the UNIT_A inbound → UNIT_B outbound pairing logic.

    Each test isolates one behavioural scenario that is likely to occur in
    real field data.
    """

    # ── Happy-path ─────────────────────────────────────────────────────────

    def test_single_match_dwell_time(self):
        """Basic match: dwell_time_s equals the timestamp gap."""
        unit_a = make_unit_df([(0, "inbound", 1000)])
        unit_b = make_unit_df([(60, "outbound", 1100)])
        result = match_events(unit_a, unit_b)
        assert len(result) == 1
        assert result.iloc[0]["dwell_time_s"] == pytest.approx(60.0)

    def test_transit_ms_sourced_from_unit_a(self):
        """transit_ms in the output must come from UNIT_A, not UNIT_B."""
        unit_a = make_unit_df([(0, "inbound", 1500)])
        unit_b = make_unit_df([(90, "outbound", 2000)])
        result = match_events(unit_a, unit_b)
        assert result.iloc[0]["transit_ms"] == 1500

    def test_walker_type_applied_after_matching(self):
        unit_a = make_unit_df([(0, "inbound", 500)])   # 500 ms → jogger
        unit_b = make_unit_df([(20, "outbound", 600)])
        result = match_events(unit_a, unit_b)
        assert result.iloc[0]["walker_type"] == "jogger"

    def test_dwell_category_applied_after_matching(self):
        unit_a = make_unit_df([(0, "inbound", 1000)])
        unit_b = make_unit_df([(15, "outbound", 1100)])   # 15 s → Transit
        result = match_events(unit_a, unit_b)
        assert result.iloc[0]["dwell_category"] == "Transit"

    def test_exit_at_exact_window_boundary_is_matched(self):
        """An exit at precisely window_s seconds must be included (≤, not <)."""
        unit_a = make_unit_df([(0, "inbound", 1000)])
        unit_b = make_unit_df([(300, "outbound", 1100)])
        result = match_events(unit_a, unit_b, window_s=300)
        assert len(result) == 1
        assert result.iloc[0]["dwell_time_s"] == pytest.approx(300.0)

    def test_two_independent_pairs_both_matched(self):
        """Two entries widely spaced in time each find their own exit."""
        unit_a = make_unit_df([(0, "inbound", 1000), (500, "inbound", 1200)])
        unit_b = make_unit_df([(60, "outbound", 1100), (560, "outbound", 1300)])
        result = match_events(unit_a, unit_b)
        assert len(result) == 2
        dwells = sorted(result["dwell_time_s"].tolist())
        assert dwells == pytest.approx([60.0, 60.0])

    # ── No-match scenarios ─────────────────────────────────────────────────

    def test_empty_unit_b_raises(self):
        """No UNIT_B events at all → ValueError."""
        unit_a = make_unit_df([(0, "inbound", 1000)])
        unit_b = make_unit_df([])
        with pytest.raises(ValueError, match="No matched events"):
            match_events(unit_a, unit_b)

    def test_exit_one_second_beyond_window_raises(self):
        """An exit 1 s beyond the window must not match."""
        unit_a = make_unit_df([(0, "inbound", 1000)])
        unit_b = make_unit_df([(301, "outbound", 1100)])
        with pytest.raises(ValueError, match="No matched events"):
            match_events(unit_a, unit_b, window_s=300)

    def test_exit_before_entry_raises(self):
        """A UNIT_B event that precedes the UNIT_A entry must not match."""
        unit_a = make_unit_df([(100, "inbound", 1000)])
        unit_b = make_unit_df([(50, "outbound", 1100)])   # exit before entry
        with pytest.raises(ValueError, match="No matched events"):
            match_events(unit_a, unit_b)

    def test_wrong_direction_unit_a_raises(self):
        """Only 'inbound' events from UNIT_A are eligible entries."""
        unit_a = make_unit_df([(0, "outbound", 1000)])    # wrong direction
        unit_b = make_unit_df([(60, "outbound", 1100)])
        with pytest.raises(ValueError, match="No matched events"):
            match_events(unit_a, unit_b)

    def test_wrong_direction_unit_b_raises(self):
        """Only 'outbound' events from UNIT_B are eligible exits."""
        unit_a = make_unit_df([(0, "inbound", 1000)])
        unit_b = make_unit_df([(60, "inbound", 1100)])    # wrong direction
        with pytest.raises(ValueError, match="No matched events"):
            match_events(unit_a, unit_b)

    # ── Simultaneous / overlapping entries ────────────────────────────────

    def test_simultaneous_entries_only_first_claims_exit(self):
        """
        Two UNIT_A entries 2 s apart with one UNIT_B exit.
        The first entry matches; the second has no exit and is silently dropped.
        """
        unit_a = make_unit_df([(0, "inbound", 1000), (2, "inbound", 1200)])
        unit_b = make_unit_df([(60, "outbound", 1100)])
        result = match_events(unit_a, unit_b)
        assert len(result) == 1
        assert result.iloc[0]["dwell_time_s"] == pytest.approx(60.0)

    def test_unit_b_event_cannot_be_reused(self):
        """
        Two UNIT_A entries close together with one UNIT_B exit.
        The exit must not match both entries.
        """
        unit_a = make_unit_df([(0, "inbound", 1000), (10, "inbound", 1200)])
        unit_b = make_unit_df([(60, "outbound", 1100)])
        result = match_events(unit_a, unit_b)
        assert len(result) == 1

    def test_simultaneous_entries_two_exits_both_match(self):
        """
        Two entries and two separate exits → two independent matches.
        Neither exit is reused.
        """
        unit_a = make_unit_df([(0, "inbound", 1000), (5, "inbound", 1200)])
        unit_b = make_unit_df([(60, "outbound", 1100), (120, "outbound", 1300)])
        result = match_events(unit_a, unit_b)
        assert len(result) == 2

    # ── Multiple candidates in window ─────────────────────────────────────

    def test_takes_earliest_unit_b_candidate(self):
        """
        When two UNIT_B exits are both within the window, the closer one wins.
        Verifies greedy-earliest matching, not greedy-latest.
        """
        unit_a = make_unit_df([(0, "inbound", 1000)])
        # 60 s exit appears first in the DataFrame (sort_values ensures this)
        unit_b = make_unit_df([(60, "outbound", 900), (180, "outbound", 1100)])
        result = match_events(unit_a, unit_b)
        assert len(result) == 1
        assert result.iloc[0]["dwell_time_s"] == pytest.approx(60.0)

    def test_second_entry_claims_remaining_exit(self):
        """
        First entry takes the earliest exit; second entry takes the next one.
        """
        unit_a = make_unit_df([(0, "inbound", 1000), (10, "inbound", 1200)])
        unit_b = make_unit_df([(60, "outbound", 1100), (120, "outbound", 1300)])
        result = match_events(unit_a, unit_b)
        assert len(result) == 2
        assert result.iloc[0]["dwell_time_s"] == pytest.approx(60.0)
        assert result.iloc[1]["dwell_time_s"] == pytest.approx(110.0)  # 120 - 10

    # ── Rain-day gap scenario ──────────────────────────────────────────────

    def test_rain_gap_events_on_different_days_still_match(self):
        """
        Events from different calendar days (e.g. after a rain washout gap)
        must still match provided they fall within window_s of each other.
        This verifies that matching is purely timestamp-based, not date-based.
        """
        day1_entry = pd.Timestamp("2025-06-14 23:59:30")
        day2_exit  = pd.Timestamp("2025-06-15 00:00:00")   # 30 s later, next day
        unit_a = pd.DataFrame([{
            "ts": day1_entry, "direction": "inbound",
            "beam": 1, "transit_ms": 1000,
        }])
        unit_b = pd.DataFrame([{
            "ts": day2_exit, "direction": "outbound",
            "beam": 1, "transit_ms": 1100,
        }])
        result = match_events(unit_a, unit_b, window_s=300)
        assert len(result) == 1
        assert result.iloc[0]["dwell_time_s"] == pytest.approx(30.0)


# ── add_phase ─────────────────────────────────────────────────────────────────

class TestAddPhase:
    """Tests for project-phase labelling based on entry timestamp."""

    def _single_row(self, date_str):
        """Minimal matched-traversal DataFrame with one entry at date_str."""
        return pd.DataFrame([{
            "entry_ts": pd.Timestamp(date_str),
            "exit_ts":  pd.Timestamp(date_str) + pd.Timedelta(seconds=60),
            "dwell_time_s": 60.0,
            "transit_ms": 1000,
            "walker_type": "regular_walker",
            "dwell_category": "Pause",
        }])

    def test_day_before_intervention_is_phase_0(self):
        df = self._single_row("2025-05-31")
        result = add_phase(df, INTERVENTION_START, POST_INT_START)
        assert result.iloc[0]["phase"] == "Phase 0"

    def test_well_before_intervention_is_phase_0(self):
        df = self._single_row("2025-01-01")
        result = add_phase(df, INTERVENTION_START, POST_INT_START)
        assert result.iloc[0]["phase"] == "Phase 0"

    def test_on_intervention_start_is_week_1(self):
        df = self._single_row(INTERVENTION_START)  # 2025-06-01
        result = add_phase(df, INTERVENTION_START, POST_INT_START)
        assert result.iloc[0]["phase"] == "Week 1"

    def test_day_6_of_intervention_is_week_1(self):
        # 6 days in: still week 1 (days 0–6)
        df = self._single_row("2025-06-07")
        result = add_phase(df, INTERVENTION_START, POST_INT_START)
        assert result.iloc[0]["phase"] == "Week 1"

    def test_day_7_of_intervention_is_week_2(self):
        # 7 days in: first day of week 2
        df = self._single_row("2025-06-08")
        result = add_phase(df, INTERVENTION_START, POST_INT_START)
        assert result.iloc[0]["phase"] == "Week 2"

    def test_week_3_label(self):
        df = self._single_row("2025-06-15")   # 14 days in
        result = add_phase(df, INTERVENTION_START, POST_INT_START)
        assert result.iloc[0]["phase"] == "Week 3"

    def test_on_post_int_start_is_week_9(self):
        df = self._single_row(POST_INT_START)  # 2025-08-03
        result = add_phase(df, INTERVENTION_START, POST_INT_START)
        assert result.iloc[0]["phase"] == "Week 9"

    def test_seven_days_into_post_int_still_week_9(self):
        df = self._single_row("2025-08-09")
        result = add_phase(df, INTERVENTION_START, POST_INT_START)
        assert result.iloc[0]["phase"] == "Week 9"

    def test_week_10_label(self):
        df = self._single_row("2025-08-10")   # 7 days after POST_INT_START
        result = add_phase(df, INTERVENTION_START, POST_INT_START)
        assert result.iloc[0]["phase"] == "Week 10"

    def test_phase_column_is_ordered_categorical(self):
        """phase must be an ordered Categorical so charts sort correctly."""
        df = self._single_row(INTERVENTION_START)
        result = add_phase(df, INTERVENTION_START, POST_INT_START)
        assert hasattr(result["phase"], "cat"), "phase should be Categorical"
        assert result["phase"].cat.ordered

    def test_phase_categories_match_phase_order(self):
        df = self._single_row(INTERVENTION_START)
        result = add_phase(df, INTERVENTION_START, POST_INT_START)
        assert list(result["phase"].cat.categories) == PHASE_ORDER


# ── aggregate_weekly ──────────────────────────────────────────────────────────

class TestAggregateWeekly:
    """Tests for per-phase aggregation, with emphasis on jogger exclusion."""

    def test_joggers_excluded_from_median_dwell(self):
        """
        A jogger's short dwell must not pull down the walker median.
        walkers: [60, 80] → median 70.  jogger: 10 → must be ignored.
        """
        df = make_phase_df([
            ("Phase 0", "jogger",          "Transit", 10.0),
            ("Phase 0", "regular_walker",  "Pause",   60.0),
            ("Phase 0", "regular_walker",  "Pause",   80.0),
        ])
        result = aggregate_weekly(df)
        row = result[result["phase"] == "Phase 0"].iloc[0]
        assert row["median_dwell_s"] == pytest.approx(70.0)

    def test_total_walkers_excludes_joggers(self):
        df = make_phase_df([
            ("Phase 0", "jogger",         "Transit", 10.0),
            ("Phase 0", "regular_walker", "Pause",   60.0),
            ("Phase 0", "slow_walker",    "Dwell",  200.0),
        ])
        result = aggregate_weekly(df)
        row = result[result["phase"] == "Phase 0"].iloc[0]
        assert row["total_walkers"] == 2

    def test_total_all_includes_joggers(self):
        df = make_phase_df([
            ("Phase 0", "jogger",         "Transit", 10.0),
            ("Phase 0", "regular_walker", "Pause",   60.0),
        ])
        result = aggregate_weekly(df)
        row = result[result["phase"] == "Phase 0"].iloc[0]
        assert row["total_all_incl_joggers"] == 2

    def test_category_counts_are_correct(self):
        df = make_phase_df([
            ("Week 1", "regular_walker", "Transit",  20.0),
            ("Week 1", "regular_walker", "Transit",  25.0),
            ("Week 1", "regular_walker", "Pause",    60.0),
            ("Week 1", "slow_walker",    "Dwell",   200.0),
        ])
        result = aggregate_weekly(df)
        row = result[result["phase"] == "Week 1"].iloc[0]
        assert row["n_transit"] == 2
        assert row["n_pause"]   == 1
        assert row["n_dwell"]   == 1

    def test_proportions_sum_to_100(self):
        df = make_phase_df([
            ("Week 2", "regular_walker", "Transit",  20.0),
            ("Week 2", "regular_walker", "Pause",    60.0),
            ("Week 2", "slow_walker",    "Dwell",   200.0),
        ])
        result = aggregate_weekly(df)
        row = result[result["phase"] == "Week 2"].iloc[0]
        total = row["pct_transit"] + row["pct_pause"] + row["pct_dwell"]
        assert total == pytest.approx(100.0)

    def test_phase_with_only_joggers_has_zero_walkers(self):
        """A phase containing only joggers should show zero in walker columns."""
        df = make_phase_df([
            ("Phase 0", "jogger", "Transit", 5.0),
            ("Phase 0", "jogger", "Transit", 8.0),
        ])
        result = aggregate_weekly(df)
        row = result[result["phase"] == "Phase 0"].iloc[0]
        assert row["total_walkers"] == 0

    def test_multiple_phases_aggregated_independently(self):
        """Ensure phase grouping does not bleed values between phases."""
        df = make_phase_df([
            ("Phase 0", "regular_walker", "Pause",  40.0),
            ("Week 1",  "regular_walker", "Dwell", 200.0),
        ])
        result = aggregate_weekly(df)
        phase0 = result[result["phase"] == "Phase 0"].iloc[0]
        week1  = result[result["phase"] == "Week 1"].iloc[0]
        assert phase0["median_dwell_s"] == pytest.approx(40.0)
        assert week1["median_dwell_s"]  == pytest.approx(200.0)
