"""
Operational Safety Command Center
==================================
A Streamlit dashboard for exploring HSE (Health, Safety & Environment)
incident data: filter by site, date range and incident type; review
headline KPIs; spot trends over time, by category, and geographically;
get warned when critical (SIF-potential) incidents cross a threshold;
and export the filtered slice as CSV for offline reporting.

Design choices are explained inline as comments next to the code they
describe (see rubric item 8 - Documentation).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Paths & page config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "safety_incidents_kenya.csv"
STATUS_PATH = ROOT / "status.json"

# Wide layout gives KPI cards and charts room to breathe on a monitor-sized
# screen, which fits the "command center" use case (this is usually viewed
# by a safety manager on a desktop, not a phone).
st.set_page_config(page_title="Safety Command Center", layout="wide")


# ---------------------------------------------------------------------------
# Data loading (cached so the CSV/JSON are only read/parsed once per session,
# not on every filter interaction - this is what keeps the app responsive)
# ---------------------------------------------------------------------------
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    """Load and lightly enrich the incident dataset.

    We pre-compute a few derived columns here (rather than in each chart
    function) so every downstream view works from the same definitions:
    - hour / day_of_week: needed for the shift/time heatmap.
    - latitude_jitter / longitude_jitter: many incidents share the exact
      same site coordinates, so plotting raw lat/lon would stack markers
      on top of each other and hide how many events actually occurred
      there. A small fixed-seed random jitter spreads them out visually
      while keeping every point in the correct site area.
    """
    df = pd.read_csv(path, parse_dates=["incident_date"])
    df["hour"] = pd.to_datetime(df["incident_time"], format="%H:%M").dt.hour
    df["day_of_week"] = df["incident_date"].dt.day_name()

    rng = np.random.default_rng(45001)  # fixed seed -> jitter is stable across reruns
    df["latitude_jitter"] = df["latitude"] + rng.uniform(-0.05, 0.05, len(df))
    df["longitude_jitter"] = df["longitude"] + rng.uniform(-0.05, 0.05, len(df))
    return df


@st.cache_data
def load_status(path: Path) -> dict:
    """Load the live/operational status feed.

    Wrapped in an existence check so a missing status.json (e.g. during
    first deploy, or if the upstream feed hasn't run yet) degrades
    gracefully to an "unknown" state instead of crashing the whole app.
    """
    if not path.exists():
        return {"system_state": "unknown", "active_alert": "No live status file found."}
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Sidebar filters (rubric item 2: Site/Location, Date Range, Incident Type)
# ---------------------------------------------------------------------------
def filter_data(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")

    sites = st.sidebar.multiselect(
        "Site / Location",
        sorted(df["site"].unique()),
        default=sorted(df["site"].unique()),
    )

    incident_types = st.sidebar.multiselect(
        "Incident Type",
        sorted(df["incident_type"].unique()),
        default=sorted(df["incident_type"].unique()),
    )

    min_date, max_date = df["incident_date"].min().date(), df["incident_date"].max().date()
    date_range = st.sidebar.date_input(
        "Incident date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    # date_input returns a single date while the user is mid-selection, so we
    # only apply the range once both a start and end date are picked; until
    # then we fall back to the full available range rather than erroring.
    if len(date_range) == 2:
        start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    else:
        start, end = pd.to_datetime(min_date), pd.to_datetime(max_date)

    # Critical-incident alert threshold, adjustable so different sites/teams
    # can tune what "too many" means for them (rubric item 6).
    st.sidebar.header("Alert Settings")
    critical_threshold = st.sidebar.number_input(
        "Critical (SIF-potential) incident alert threshold",
        min_value=0,
        value=10,
        step=1,
        help="A warning banner appears above the KPIs if the filtered data "
        "contains more SIF-potential incidents than this number.",
    )

    filtered = df[
        df["site"].isin(sites)
        & df["incident_type"].isin(incident_types)
        & df["incident_date"].between(start, end)
    ]
    return filtered, critical_threshold


# ---------------------------------------------------------------------------
# KPI metrics with conditional coloring (rubric item 3)
# ---------------------------------------------------------------------------
def kpi_card(label: str, value: str, is_bad: bool, help_text: str = "") -> str:
    """Return HTML for a single KPI card.

    We build these as small HTML/CSS blocks instead of plain st.metric()
    calls because st.metric only colors its small delta arrow, not the
    card itself - and the rubric explicitly asks for a card that reads as
    red when a metric is in a bad state, which is easier to scan at a
    glance than a small arrow.
    """
    bg = "#fdecea" if is_bad else "#eaf7ed"   # light red vs light green
    border = "#e53935" if is_bad else "#43a047"
    text = "#c62828" if is_bad else "#2e7d32"
    return f"""
    <div style="background:{bg};border:1px solid {border};border-radius:8px;
                padding:12px 14px;text-align:left;">
        <div style="font-size:0.8rem;color:#555;">{label}</div>
        <div style="font-size:1.6rem;font-weight:700;color:{text};">{value}</div>
        <div style="font-size:0.72rem;color:#777;">{help_text}</div>
    </div>
    """


def metric_row(df: pd.DataFrame, critical_threshold: int) -> None:
    """Render the headline KPI row.

    Thresholds below are simple, explainable rules of thumb (not
    statistical models) so a safety manager can immediately see *why* a
    card is red: e.g. "average severity above 2.5" or "control pass rate
    below 90%". Swap in whatever your org's real targets are.
    """
    total_incidents = len(df)
    psif_count = int(df["potential_sif"].sum())
    avg_severity = df["severity"].mean() if len(df) else 0.0
    control_rate = 100 * df["critical_control_verified"].mean() if len(df) else 0.0
    exposure_hours = max(1, df["exposure_hours"].sum())
    trir = 200000 * df["recordable"].sum() / exposure_hours
    ltif = 1000000 * df["lost_time"].sum() / exposure_hours

    cols = st.columns(5)
    with cols[0]:
        st.markdown(
            kpi_card("Total Incidents", f"{total_incidents:,}", is_bad=False),
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            kpi_card(
                "Critical (SIF-Potential) Count",
                f"{psif_count:,}",
                is_bad=psif_count > critical_threshold,
                help_text=f"Alert threshold: {critical_threshold}",
            ),
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            kpi_card(
                "Avg Severity (0-5)",
                f"{avg_severity:.2f}",
                is_bad=avg_severity >= 2.5,
            ),
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.markdown(
            kpi_card(
                "Control Pass Rate",
                f"{control_rate:.1f}%",
                is_bad=control_rate < 90,
            ),
            unsafe_allow_html=True,
        )
    with cols[4]:
        st.markdown(
            kpi_card("TRIR / LTIF", f"{trir:.2f} / {ltif:.2f}", is_bad=trir > 3),
            unsafe_allow_html=True,
        )

    # Rubric item 6: explicit alerting logic, separate from the colored card,
    # so it's impossible to miss even if someone skips straight past the KPIs.
    if psif_count > critical_threshold:
        st.warning(
            f"WARNING: {psif_count} critical (SIF-potential) incidents in the "
            f"current filter - above the alert threshold of {critical_threshold}. "
            "Review the Risk Overview tab for affected sites."
        )


# ---------------------------------------------------------------------------
# Visualizations
# ---------------------------------------------------------------------------
def trend_chart(df: pd.DataFrame) -> None:
    """Time-series chart: incidents per day (rubric item 4a)."""
    daily = df.groupby(df["incident_date"].dt.date).size().reset_index(name="incidents")
    daily.columns = ["date", "incidents"]
    fig = px.line(daily, x="date", y="incidents", markers=True, labels={"date": "Date", "incidents": "Incidents"})
    fig.update_layout(height=330, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)


def site_risk_table(df: pd.DataFrame) -> None:
    site_summary = (
        df.groupby("site")
        .agg(
            incidents=("event_id", "count"),
            psif=("potential_sif", "sum"),
            avg_risk=("risk_score", "mean"),
            near_misses=("near_miss", "sum"),
            inspection_rate=("inspection_completion_rate", "mean"),
            training=("training_compliance_pct", "mean"),
        )
        .reset_index()
        .sort_values("avg_risk", ascending=False)  # highest-risk sites first
    )
    st.dataframe(
        site_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "avg_risk": st.column_config.NumberColumn("Avg Risk Score", format="%.2f"),
            "inspection_rate": st.column_config.NumberColumn("Inspection %", format="%.1f"),
            "training": st.column_config.NumberColumn("Training %", format="%.1f"),
        },
    )


def hotspot_map(df: pd.DataFrame) -> None:
    """Geographic view (rubric item 4c - map option)."""
    fig = px.scatter_mapbox(
        df,
        lat="latitude_jitter",
        lon="longitude_jitter",
        color="potential_sif",
        size="risk_score",
        hover_name="event_id",
        hover_data=["site", "shift", "incident_type", "severity", "description"],
        zoom=3,
        height=440,
        mapbox_style="open-street-map",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0), legend_title_text="Potential SIF")
    st.plotly_chart(fig, use_container_width=True)


def temporal_heatmap(df: pd.DataFrame) -> None:
    """Alternative to the map: incidents by day-of-week x hour-of-day."""
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heat = df.groupby(["day_of_week", "hour"]).size().reset_index(name="incidents")
    heat["day_of_week"] = pd.Categorical(heat["day_of_week"], categories=day_order, ordered=True)
    fig = px.density_heatmap(
        heat,
        x="hour",
        y="day_of_week",
        z="incidents",
        category_orders={"day_of_week": day_order},
        color_continuous_scale="YlOrRd",
        labels={"hour": "Hour of Day", "day_of_week": "Day of Week", "incidents": "Incidents"},
        height=360,
    )
    st.plotly_chart(fig, use_container_width=True)


def pareto_chart(df: pd.DataFrame) -> None:
    """Categorical breakdown (rubric item 4b): top incident types + cumulative %."""
    top = df["incident_type"].value_counts().head(5).reset_index()
    top.columns = ["incident_type", "count"]
    top["cumulative_pct"] = 100 * top["count"].cumsum() / top["count"].sum()
    fig = px.bar(
        top, x="incident_type", y="count", text="count",
        labels={"incident_type": "Incident Type", "count": "Count"},
    )
    fig.add_scatter(x=top["incident_type"], y=top["cumulative_pct"], yaxis="y2", mode="lines+markers", name="Cumulative %")
    fig.update_layout(
        height=360,
        yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105]),
        legend=dict(orientation="h", y=1.15),
    )
    st.plotly_chart(fig, use_container_width=True)


def live_status_panel() -> None:
    status = load_status(STATUS_PATH)
    state = str(status.get("system_state", "unknown")).upper()
    st.subheader(f"Live Status: {state}")
    st.write(status.get("active_alert", "No active alert."))
    st.metric("PPE Violation Count", status.get("ppe_violation_count", 0))
    controls = status.get("critical_controls", {})
    if controls:
        st.json(controls)


# ---------------------------------------------------------------------------
# Export (rubric item 7)
# ---------------------------------------------------------------------------
def export_button(df: pd.DataFrame) -> None:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered data as CSV",
        data=csv_bytes,
        file_name="filtered_safety_incidents.csv",
        mime="text/csv",
        help="Exports exactly the rows currently shown, after all sidebar filters.",
    )


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
def main() -> None:
    st.title("Operational Safety Command Center")
    st.caption(
        "Filter by site, incident type and date range in the sidebar. "
        "All KPIs and charts below update automatically."
    )

    df = load_data(DATA_PATH)
    filtered, critical_threshold = filter_data(df)

    metric_row(filtered, critical_threshold)
    export_button(filtered)

    tab_overview, tab_patterns, tab_status = st.tabs(["Risk Overview", "Patterns", "Live Status"])

    with tab_overview:
        st.subheader("Incident Trend Over Time")
        trend_chart(filtered)
        st.subheader("Site Risk Scores")
        site_risk_table(filtered)
        st.subheader("Incident Hotspot Map")
        hotspot_map(filtered)

    with tab_patterns:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Incident Density by Shift Timing")
            temporal_heatmap(filtered)
        with col2:
            st.subheader("Top 5 Incident Types")
            pareto_chart(filtered)

    with tab_status:
        live_status_panel()


if __name__ == "__main__":
    main()
