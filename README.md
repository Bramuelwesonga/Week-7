# Operational Safety Command Center Lab Files

This folder contains the files needed to complete the Streamlit safety dashboard lab.

## Files

- `data/safety_incidents_Kenya.csv`: Synthetic HSE dataset with incidents, near misses, inspections, training, coordinates, severity, SIF potential, and exposure hours.
- `app_safety_dashboard.py`: Streamlit dashboard with cached loading, sidebar filters, KPI metrics, hotspot map, temporal heatmap, Pareto chart, and optional live status panel.


## Run

```powershell
python -m pip install -r requirements.txt
streamlit run app_safety_dashboard.py
```
# Code Writeup: Operational Safety Command Center Dashboard

## 1. Purpose of the Code

The code defines a **Streamlit-based safety analytics dashboard** called the **Operational Safety Command Center**.

Its main purpose is to help safety managers, supervisors, and operational leaders monitor workplace safety incidents and identify risk patterns. The dashboard brings together:

- Historical safety incident records
- Safety performance metrics
- Site-level risk comparisons
- Geographic incident hotspots
- Time-based incident patterns
- Common incident types
- Live system status and alerts

In practical terms, the application is designed to answer questions such as:

- How many safety incidents occurred?
- Which incidents could potentially become serious or fatal?
- Which sites have the highest average risk?
- Are incidents clustered in particular locations?
- What days or times of day are higher risk?
- What are the most common incident types?
- Are critical controls being verified?
- Is there any live safety alert or abnormal system state?

The code is therefore not just a reporting tool. It is intended to act as a **decision-support interface** for safety operations.

---

## 2. High-Level Intent

The application is built around a common operational safety workflow:

1. **Load safety incident data**
2. **Allow the user to filter the data**
3. **Show headline safety metrics**
4. **Show risk by site**
5. **Show incident hotspots on a map**
6. **Show time-based patterns**
7. **Show the most frequent incident types**
8. **Show live safety status information**

The intent is to move the user from raw incident records to operational insight quickly.

The dashboard is organized into three tabs:

| Tab | Purpose |
|---|---|
| **Risk Overview** | Shows site-level risk summary and incident map |
| **Patterns** | Shows time-based incident trends and top incident types |
| **Live Status** | Shows current safety alerts and control status |

---

## 3. Expected Data Inputs

The application expects two main data sources.

### 3.1 Incident Data

The main dataset is expected to be a CSV file located at:

```python
data/safety_incidents.csv
```

This file likely contains one row per safety incident. Based on the code, expected columns include:

- `event_id`
- `site`
- `incident_date`
- `incident_time`
- `latitude`
- `longitude`
- `shift`
- `incident_type`
- `severity`
- `description`
- `potential_sif`
- `risk_score`
- `recordable`
- `lost_time`
- `near_miss`
- `critical_control_verified`
- `exposure_hours`
- `inspection_completion_rate`
- `training_compliance_pct`

Some of these columns are used directly in metrics, while others are used for filtering, grouping, map display, or hover information.

### 3.2 Live Status Data

The live status file is expected at:

```python
status.json
```

This file is expected to contain JSON data such as:

```json
{
  "system_state": "normal",
  "active_alert": "No active alert.",
  "ppe_violation_count": 2,
  "critical_controls": {
    "gas_detection": "OK",
    "emergency_stop": "OK"
  }
}
```

The dashboard uses this file to show live safety status, active alerts, PPE violations, and critical control states.

---

## 4. Application Structure

The code is organized into several functions. Each function has a clear responsibility.

The main flow is:

```python
main()
```

Inside `main()`:

1. The page title is displayed.
2. The incident dataset is loaded.
3. Filters are applied.
4. Headline metrics are shown.
5. The dashboard tabs are rendered.

Simplified execution flow:

```text
Start
  |
  |--> Load incident CSV
  |
  |--> Apply site/date filters
  |
  |--> Show safety KPIs
  |
  |--> Show Risk Overview tab
  |
  |--> Show Patterns tab
  |
  |--> Show Live Status tab
```

---

## 5. Detailed Function Explanations

---

## 5.1 Data Loading Function

```python
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
```

### Purpose

This function loads and prepares the incident dataset for analysis.

### What It Does

1. Reads the CSV file using Pandas.
2. Converts `incident_date` into a datetime type.
3. Extracts the hour from `incident_time`.
4. Extracts the day of the week from `incident_date`.
5. Adds random latitude and longitude jitter.
6. Returns the prepared DataFrame.

### Why This Matters

Safety dashboards often require time-based analysis. By extracting `hour` and `day_of_week`, the code enables patterns such as:

- Which shift times have more incidents?
- Which days of the week are riskier?
- Are incidents concentrated around certain hours?

The random jitter is added to slightly disperse map points. This is useful when multiple incidents occur near the same geographic location. Without jitter, points could overlap heavily and hide the true number of incidents.

### Caching

The decorator:

```python
@st.cache_data
```

tells Streamlit to cache the result. This improves performance because the CSV is not reloaded every time the user interacts with the app.

---

## 5.2 Live Status Loading Function

```python
@st.cache_data
def load_status(path: Path) -> dict:
```

### Purpose

This function loads live operational safety status information from a JSON file.

### What It Does

- If the status file exists, it reads and parses the JSON.
- If the file does not exist, it returns a default status:

```python
{
    "system_state": "unknown",
    "active_alert": "No live status file found."
}
```

### Why This Matters

This makes the dashboard more robust. If the live status file is missing, the app does not crash. Instead, it shows a clear fallback message.

This is important for operational dashboards because missing files can occur during:

- Deployment
- System startup
- Data pipeline delays
- Configuration errors

---

## 5.3 Filtering Function

```python
def filter_data(df: pd.DataFrame) -> pd.DataFrame:
```

### Purpose

This function creates interactive filters in the Streamlit sidebar.

### Filters Provided

The user can filter by:

1. **Site**
2. **Incident date range**

### Site Filter

The code creates a multiselect box containing all unique sites:

```python
sites = st.sidebar.multiselect(...)
```

This allows the user to analyze one site, multiple sites, or all sites.

### Date Filter

The date filter allows the user to choose a start and end date.

If a valid two-date range is selected, the data is filtered to that range. If not, the full available date range is used.

### Why This Matters

Safety teams often need to answer focused questions, such as:

- What happened at Site A last month?
- Which sites had incidents during a specific period?
- Has incident frequency changed after a new safety policy?

Filters make the dashboard flexible and user-driven.

---

## 5.4 Headline Metrics Function

```python
def metric_row(df: pd.DataFrame) -> None:
```

### Purpose

This function displays five key safety performance indicators.

### Metrics Shown

| Metric | Meaning |
|---|---|
| Total Incidents | Number of filtered incidents |
| SIF-Potential Count | Number of incidents with potential for serious injury or fatality |
| Control Pass Rate | Percentage of incidents where critical controls were verified |
| TRIR | Total Recordable Incident Rate |
| LTIF | Lost Time Injury Frequency |

---

### Total Incidents

```python
total_incidents = len(df)
```

This counts all incidents remaining after filtering.

---

### SIF-Potential Count

```python
psif_count = int(df["potential_sif"].sum())
```

SIF usually stands for **Serious Injury or Fatality**.

This metric counts incidents flagged as having serious potential. It helps users focus on high-consequence risks, not just frequent minor events.

---

### Control Pass Rate

```python
control_rate = 100 * df["critical_control_verified"].mean()
```

This calculates the percentage of incidents where critical controls were verified.

For example, if `critical_control_verified` contains boolean or binary values such as:

```text
True / False
1 / 0
```

then the average represents the proportion of verified controls.

This metric helps assess whether safety controls are functioning as expected.

---

### TRIR

```python
trir = 200000 * df["recordable"].sum() / exposure_hours
```

TRIR stands for **Total Recordable Incident Rate**.

The formula used is:

```text
TRIR = Number of recordable incidents × 200,000 / exposure hours
```

The value `200,000` is a common safety normalization constant representing 100 full-time workers working 40 hours per week for 50 weeks.

This allows organizations to compare safety performance across different workforce sizes and time periods.

---

### LTIF

```python
ltif = 1000000 * df["lost_time"].sum() / exposure_hours
```

LTIF stands for **Lost Time Injury Frequency**.

The formula used is:

```text
LTIF = Number of lost-time injuries × 1,000,000 / exposure hours
```

This metric focuses on more severe incidents that result in lost work time.

### Why This Section Matters

The metric row gives users an immediate executive-level view of safety performance.

A user can quickly see:

- How many incidents occurred
- How serious they may be
- Whether controls are working
- How the organization performs against standard safety rates

---

## 5.5 Site Risk Table Function

```python
def site_risk_table(df: pd.DataFrame) -> None:
```

### Purpose

This function summarizes safety performance by site.

### Grouping Logic

The data is grouped by `site`, then aggregated to calculate:

| Output Column | Meaning |
|---|---|
| incidents | Number of incidents at the site |
| psif | Number of SIF-potential incidents |
| avg_risk | Average risk score |
| near_misses | Number of near-miss events |
| inspection_rate | Average inspection completion rate |
| training | Average training compliance percentage |

### Sorting

The table is sorted by average risk score in descending order:

```python
.sort_values("avg_risk", ascending=False)
```

This means the highest-risk sites appear first.

### Why This Matters

This table helps users compare sites.

It supports questions such as:

- Which site has the highest average risk?
- Which sites have many near misses?
- Are low inspection rates associated with higher risk?
- Are training compliance levels related to incident frequency?

The table is useful for prioritization and resource allocation.

---

## 5.6 Hotspot Map Function

```python
def hotspot_map(df: pd.DataFrame) -> None:
```

### Purpose

This function displays incidents on a geographic map.

### Map Variables

The map uses:

- Latitude: `latitude_jitter`
- Longitude: `longitude_jitter`
- Color: `potential_sif`
- Size: `risk_score`
- Hover details: site, shift, incident type, severity, description

### Why Jitter Is Used

The jittered coordinates slightly spread out incidents that may otherwise have identical or very similar locations.

This improves visibility when multiple incidents occur in the same area.

### Why Color and Size Matter

Using `potential_sif` for color helps distinguish incidents with serious potential.

Using `risk_score` for size helps show which incidents carry higher risk.

### Why This Matters

Maps are useful for identifying spatial patterns. For example:

- Are incidents clustered around a particular facility area?
- Do certain regions have more severe incidents?
- Are high-risk incidents geographically concentrated?

This supports location-based safety interventions.

---

## 5.7 Temporal Heatmap Function

```python
def temporal_heatmap(df: pd.DataFrame) -> None:
```

### Purpose

This function shows when incidents occur by day of week and hour of day.

### How It Works

It groups incidents by:

- `day_of_week`
- `hour`

Then it counts the number of incidents in each combination.

The result is displayed as a density heatmap.

### Day Ordering

The days are explicitly ordered:

```python
Monday
Tuesday
Wednesday
Thursday
Friday
Saturday
Sunday
```

This makes the chart easier to read.

### Why This Matters

Time-based patterns are critical in safety analysis.

The heatmap can reveal patterns such as:

- More incidents during night shifts
- Higher incident frequency near shift changes
- Weekend risk spikes
- Fatigue-related time periods
- High-risk operational hours

This helps teams target training, supervision, or controls to specific times.

---

## 5.8 Pareto Chart Function

```python
def pareto_chart(df: pd.DataFrame) -> None:
```

### Purpose

This function shows the top five incident types and their cumulative percentage.

### What It Does

1. Counts incidents by `incident_type`.
2. Takes the top five categories.
3. Calculates cumulative percentage.
4. Displays a bar chart of counts.
5. Adds a line showing cumulative percentage.

### Why This Is Called a Pareto Chart

This is based on the Pareto principle, often summarized as:

> A small number of causes may account for a large percentage of incidents.

For example, if slips, trips, and falls make up 60% of incidents, safety leaders may prioritize controls in that area.

### Why This Matters

It helps users focus on the most impactful incident categories.

Instead of treating all incident types equally, the chart helps answer:

- Which incident types should be addressed first?
- Which few categories create most of the volume?
- Where should corrective actions be focused?

---

## 5.9 Live Status Panel Function

```python
def live_status_panel() -> None:
```

### Purpose

This function displays live or near-live safety status information.

### What It Shows

It shows:

1. System state
2. Active alert message
3. PPE violation count
4. Critical controls in JSON format

### Example Information

The panel may show:

```text
Live Status: NORMAL
No active alert.
PPE Violation Count: 3
```

Then it may show critical controls such as:

```json
{
  "gas_detection": "OK",
  "fire_suppression": "FAULT",
  "emergency_stop": "OK"
}
```

### Why This Matters

This section shifts the dashboard from purely historical analysis to operational monitoring.

It helps users see not only what has happened, but also what may be happening now.

This is important for rapid response.

---

## 5.10 Main Dashboard Function

```python
def main() -> None:
```

### Purpose

This function controls the overall dashboard layout.

### What It Does

It performs the following steps:

1. Sets the dashboard title.
2. Loads incident data.
3. Applies filters.
4. Displays KPI metrics.
5. Creates three tabs:
   - Risk Overview
   - Patterns
   - Live Status

### Risk Overview Tab

This tab contains:

- Site risk table
- Incident hotspot map

### Patterns Tab

This tab contains:

- Incident density by shift timing
- Top five incident types

### Live Status Tab

This tab contains:

- Current system state
- Active alert
- PPE violations
- Critical controls

### Why Tabs Are Used

Tabs reduce visual clutter.

Instead of showing everything at once, the dashboard organizes information by analytical goal:

- Risk overview
- Pattern discovery
- Live monitoring

This improves usability.

---

## 6. Overall Data Flow

The application follows this data flow:

```text
CSV File
   |
   v
load_data()
   |
   v
filter_data()
   |
   v
metric_row()
   |
   v
Tabs:
   |--> site_risk_table()
   |--> hotspot_map()
   |--> temporal_heatmap()
   |--> pareto_chart()

JSON File
   |
   v
load_status()
   |
   v
live_status_panel()
```

This separation makes the code easier to understand and maintain.

---

## 7. Key Analytical Concepts Used

The dashboard combines several important safety analytics concepts.

### 7.1 Incident Frequency

The dashboard counts incidents and groups them by site, type, day, and hour.

This helps identify where and when incidents happen.

### 7.2 Incident Severity

Fields such as:

- `potential_sif`
- `risk_score`
- `recordable`
- `lost_time`

allow the dashboard to distinguish between minor events and serious events.

### 7.3 Control Effectiveness

The field:

- `critical_control_verified`

helps evaluate whether controls are in place and functioning.

### 7.4 Operational Readiness

The live status panel shows current alerts and control states.

This supports real-time awareness.

### 7.5 Preventive Insight

Near misses, training compliance, inspection rates, and time-based patterns help identify risks before they become major incidents.

---

## 8. Intended User Benefits

This dashboard is designed to help users:

### Detect Risk Quickly

KPIs and high-risk site tables allow rapid identification of problem areas.

### Prioritize Actions

Pareto analysis and risk scoring help users focus on the most important issues.

### Understand Timing

The heatmap reveals when incidents are most likely to occur.

### Understand Location

The map reveals where incidents are concentrated.

### Monitor Live Conditions

The live status panel helps users identify current alerts or control failures.

---

## 9. Educational Summary for Learners

A learner can understand this code as a complete analytics pipeline:

1. **Input**: Safety incident data and live status data are loaded.
2. **Preparation**: Dates, times, weekdays, and map coordinates are processed.
3. **Interaction**: Users filter by site and date.
4. **Analysis**: Metrics, tables, maps, heatmaps, and charts are generated.
5. **Presentation**: Results are displayed in a Streamlit dashboard.
6. **Decision Support**: The dashboard helps safety teams act on risk.

In simple terms, the code turns raw safety records into a visual command center.

---

## 10. Important Implementation Note

The provided code appears to contain formatting artifacts that would prevent it from running exactly as written.

Examples include:

```python
from future import annotations
ROOT = Path(file).resolve().parent
```

These likely should be:

```python
from __future__ import annotations
ROOT = Path(__file__).resolve().parent
```

Also, several strings and identifiers contain extra spaces, such as:

```python
"incident_date "
"site "
"incident_time "
```

In a working Python file, these would normally be:

```python
"incident_date"
"site"
"incident_time"
```

Similarly, the final block:

```python
if name == "main":
    main()
```

would normally be:

```python
if __name__ == "__main__":
    main()
```

These issues do not change the overall intent of the code, but they are important if the learner wants to run or modify it.

---

## 11. Short Summary

The code builds an **Operational Safety Command Center** using Streamlit, Pandas, NumPy, and Plotly.

It loads safety incident data, lets users filter by site and date, calculates safety KPIs, compares risk across sites, maps incident hotspots, analyzes incident timing, identifies top incident types, and displays live safety status.

Its intent is to help safety professionals quickly understand risk, detect patterns, and respond to operational safety issues more effectively.
