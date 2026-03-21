import os
import streamlit as st
import fastf1
import pandas as pd

CACHE_DIR = "/tmp/fastf1_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

st.title("🏎️ FastF1 Analytics")

# --- Controls ---
col1, col2, col3 = st.columns(3)
year = col1.selectbox("Season", [2025, 2024, 2023])


@st.cache_data(ttl=86400, show_spinner=False)
def get_schedule(year: int) -> pd.DataFrame:
    return fastf1.get_event_schedule(year, include_testing=False)[
        ["RoundNumber", "EventName", "Country", "EventDate"]
    ].copy()


with st.spinner("Loading calendar..."):
    try:
        schedule = get_schedule(year)
    except Exception as e:
        st.error(f"Could not load calendar: {e}")
        st.stop()

event_map = {row.EventName: int(row.RoundNumber) for row in schedule.itertuples()}
event_name = col2.selectbox("Grand Prix", list(event_map.keys()))
session_label = col3.selectbox("Session", ["Race", "Qualifying"])
session_code = {"Race": "R", "Qualifying": "Q"}[session_label]


@st.cache_data(ttl=3600, show_spinner=False)
def load_session(year: int, round_num: int, stype: str):
    session = fastf1.get_session(year, round_num, stype)
    session.load(telemetry=False, weather=False, messages=False)
    laps = session.laps[
        ["Driver", "Team", "LapNumber", "LapTime", "Compound", "IsPersonalBest"]
    ].copy()
    laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()
    results = session.results.copy()
    return laps, results


with st.spinner(f"Loading {event_name} {session_label}..."):
    try:
        laps, results = load_session(year, event_map[event_name], session_code)
    except Exception as e:
        st.error(f"Could not load session: {e}")
        st.stop()

st.divider()

# ── RACE ──────────────────────────────────────────────────────────────────────
if session_label == "Race":
    # Metrics
    winner = results.iloc[0]
    fastest = laps[laps["IsPersonalBest"] == True].nsmallest(1, "LapTimeSec")
    m1, m2, m3 = st.columns(3)
    m1.metric("Winner", winner.get("Abbreviation", "—"))
    m2.metric("Team", winner.get("TeamName", "—"))
    if not fastest.empty:
        fl = fastest.iloc[0]
        m3.metric("Fastest Lap", f"{fl['Driver']}  {fl['LapTimeSec']:.3f}s")

    st.divider()

    # Results table
    st.subheader("Race Results")
    race_cols = [c for c in ["Position", "Abbreviation", "FullName", "TeamName", "GridPosition", "Points", "Status"] if c in results.columns]
    display = results[race_cols].copy()
    if "Position" in display.columns:
        display["Position"] = pd.to_numeric(display["Position"], errors="coerce").astype("Int64")
    if "Points" in display.columns:
        display["Points"] = pd.to_numeric(display["Points"], errors="coerce").astype("Int64")
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()

    # Lap time chart – top 5 finishers only to keep chart readable
    st.subheader("Lap time evolution — top 5 finishers")
    top5 = results["Abbreviation"].head(5).tolist()
    chart_laps = (
        laps[laps["Driver"].isin(top5)]
        .dropna(subset=["LapTimeSec"])
        .query("LapTimeSec < LapTimeSec.quantile(0.99)")  # drop safety car outliers
    )
    if not chart_laps.empty:
        pivot = chart_laps.pivot_table(
            index="LapNumber", columns="Driver", values="LapTimeSec", aggfunc="median"
        )
        st.line_chart(pivot)
    else:
        st.info("No lap time data available.")

    st.divider()

    # Compound / stint breakdown
    st.subheader("Tyre compounds used")
    compounds = (
        laps.dropna(subset=["Compound"])
        .groupby(["Driver", "Compound"])
        .size()
        .reset_index(name="Laps")
        .sort_values(["Driver", "Compound"])
    )
    st.dataframe(compounds, use_container_width=True, hide_index=True)


# ── QUALIFYING ────────────────────────────────────────────────────────────────
else:
    pole = results.iloc[0]
    m1, m2 = st.columns(2)
    m1.metric("Pole Position", pole.get("Abbreviation", "—"))
    m2.metric("Team", pole.get("TeamName", "—"))

    st.divider()

    # Results table
    st.subheader("Qualifying Results")
    q_cols = [c for c in ["Position", "Abbreviation", "FullName", "TeamName", "Q1", "Q2", "Q3"] if c in results.columns]
    display = results[q_cols].copy()

    # Format timedelta Q columns as mm:ss.sss strings
    for col in ["Q1", "Q2", "Q3"]:
        if col in display.columns:
            display[col] = display[col].apply(
                lambda t: f"{int(t.total_seconds() // 60)}:{t.total_seconds() % 60:06.3f}"
                if pd.notnull(t) and hasattr(t, "total_seconds") else ""
            )
    if "Position" in display.columns:
        display["Position"] = pd.to_numeric(display["Position"], errors="coerce").astype("Int64")

    st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()

    # Q3 lap times bar chart
    st.subheader("Q3 lap times (top 10)")
    if "Q3" in results.columns:
        q3 = results[["Abbreviation", "Q3"]].dropna(subset=["Q3"]).head(10).copy()
        q3["Q3sec"] = q3["Q3"].apply(
            lambda t: t.total_seconds() if hasattr(t, "total_seconds") else None
        )
        q3 = q3.dropna(subset=["Q3sec"]).set_index("Abbreviation")
        if not q3.empty:
            st.bar_chart(q3["Q3sec"])
    else:
        st.info("Q3 data not available for this session.")
