import os
import streamlit as st
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from app.components import render_footer, render_session_timer, vega_metrics
from app.f1_store import get_available_years
from app.theme_utils import get_theme_class, get_vega_imports

load_dotenv(".env.local")

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8501")

COMPOUND_COLORS = {
    "SOFT": "#e8002d",
    "MEDIUM": "#ffd700",
    "HARD": "#eeeeee",
    "INTERMEDIATE": "#39b54a",
    "WET": "#0067ff",
}

st.components.v1.html(f"""
{get_vega_imports()}

<div {get_theme_class()}>
<vega-font
  variant="font-h1"
  as="h1"
  style="font-weight: bold; font-size: 4rem;"
>
  🏎️ FastF1 Analytics
</vega-font>
</div>
""", height=120)

@st.cache_data(ttl=86400, show_spinner=False)
def get_years() -> list[int]:
    return get_available_years()


@st.cache_data(ttl=86400, show_spinner=False)
def get_schedule(year: int) -> pd.DataFrame:
    resp = httpx.get(f"{BASE_URL}/f1/schedule", params={"year": year}, timeout=60)
    resp.raise_for_status()
    return pd.DataFrame(resp.json()["schedule"])


with st.spinner("Loading calendar..."):
    try:
        years = get_years()
        if not years:
            st.error("No seasons are available yet. Run the migration script to populate Turso.")
            st.stop()
        col1, col2, col3 = st.columns(3)
        with col1:
            year = st.selectbox("Season", years, index=0, key="year")
        schedule = get_schedule(year)
    except Exception as e:
        st.error(f"Could not load calendar: {e}")
        st.stop()

event_map = {row.EventName: int(row.RoundNumber) for row in schedule.itertuples()}
with col2:
    event_name = st.selectbox("Grand Prix", list(event_map.keys()), key="event")
with col3:
    session_label = st.selectbox("Session", ["Race", "Qualifying"], key="session")
session_code = {"Race": "R", "Qualifying": "Q"}[session_label]


@st.fragment
def session_sidebar_timer(session_label: str) -> None:
    duration_seconds = 7200 if session_label == "Race" else 3600
    st.markdown("### Streamlit Session Timer")
    render_session_timer("Streamlit Session Timer", duration_seconds=duration_seconds)


@st.cache_data(ttl=3600, show_spinner=False)
def load_session(year: int, round_num: int, stype: str):
    resp = httpx.get(
        f"{BASE_URL}/f1/results",
        params={"year": year, "round": round_num, "session": stype},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return pd.DataFrame(data["laps"]), pd.DataFrame(data["results"])


with st.spinner(f"Loading {event_name} {session_label}..."):
    try:
        laps, results = load_session(year, event_map[event_name], session_code)
    except Exception as e:
        st.error(f"Could not load session: {e}")
        st.stop()

with st.sidebar:
    session_sidebar_timer(session_label)

st.divider()

# ── RACE ──────────────────────────────────────────────────────────────────────
if session_label == "Race":
    winner = results.iloc[0]
    fastest = laps[laps["IsPersonalBest"] == True].nsmallest(1, "LapTimeSec") if "IsPersonalBest" in laps.columns else pd.DataFrame()

    # Top metrics
    fastest_driver = "—"
    fastest_time = "—"
    if not fastest.empty:
        fl = fastest.iloc[0]
        fastest_driver = fl["Driver"]
        fastest_time = f"{fl['LapTimeSec']:.3f}s"

    vega_metrics([
        {"label": "Winner", "value": winner.get("Abbreviation", "—")},
        {"label": "Team", "value": winner.get("TeamName", "—")},
        {"label": "Fastest Lap", "value": fastest_driver},
        {"label": "Fastest Time", "value": fastest_time},
    ])

    st.divider()

    # Lap time evolution — top 5 with animation
    st.components.v1.html("""
<vega-font
  variant="font-h4"
  as="h4"
  style="font-weight: bold;"
>
  Lap Times — Top 5 Finishers
</vega-font>
""", height=44)
    top5 = results["Abbreviation"].head(5).tolist()
    chart_laps = laps[laps["Driver"].isin(top5)].dropna(subset=["LapTimeSec"]).copy()
    if not chart_laps.empty:
        p99 = chart_laps["LapTimeSec"].quantile(0.99)
        chart_laps = chart_laps[chart_laps["LapTimeSec"] < p99]
        chart_laps["LapNumber"] = pd.to_numeric(chart_laps["LapNumber"], errors="coerce")
        chart_laps = chart_laps.dropna(subset=["LapNumber"])

        # Fixed axis ranges so scale never changes during animation
        y_min = chart_laps["LapTimeSec"].min() - 0.5
        y_max = chart_laps["LapTimeSec"].max() + 0.5
        x_max = chart_laps["LapNumber"].max()

        # Assign consistent colors to each driver
        palette = px.colors.qualitative.Plotly
        driver_color = {drv: palette[i % len(palette)] for i, drv in enumerate(top5)}

        lt_laps = sorted(chart_laps["LapNumber"].unique())

        lt_frames = []
        for lap in lt_laps:
            fd = chart_laps[chart_laps["LapNumber"] <= lap]
            lt_frames.append(go.Frame(
                data=[
                    go.Scatter(
                        x=fd[fd["Driver"] == drv]["LapNumber"].tolist(),
                        y=fd[fd["Driver"] == drv]["LapTimeSec"].tolist(),
                        mode="lines+markers",
                        name=drv,
                        line=dict(color=driver_color[drv]),
                        marker=dict(color=driver_color[drv]),
                        showlegend=True,
                    )
                    for drv in top5
                ],
                name=str(int(lap)),
            ))

        # Default to showing all laps (last frame)
        full_data = [
            go.Scatter(
                x=chart_laps[chart_laps["Driver"] == drv]["LapNumber"].tolist(),
                y=chart_laps[chart_laps["Driver"] == drv]["LapTimeSec"].tolist(),
                mode="lines+markers",
                name=drv,
                line=dict(color=driver_color[drv]),
                marker=dict(color=driver_color[drv]),
                showlegend=True,
            )
            for drv in top5
        ]

        fig_lt = go.Figure(data=full_data, frames=lt_frames)
        fig_lt.update_layout(
            xaxis=dict(title="Lap", range=[1, x_max], fixedrange=False),
            yaxis=dict(title="Lap Time (s)", range=[y_min, y_max], fixedrange=False),
            height=420,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="v", x=1.01, y=1, traceorder="normal"),
            updatemenus=[{
                "type": "buttons",
                "showactive": False,
                "y": 1.12,
                "x": 0.5,
                "xanchor": "center",
                "buttons": [
                    {"label": "▶ Play", "method": "animate", "args": [None, {"frame": {"duration": 120, "redraw": True}, "fromcurrent": False}]},
                    {"label": "⏸ Pause", "method": "animate", "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]},
                ],
            }],
            sliders=[{
                "steps": [{"args": [[f.name], {"frame": {"duration": 120}, "mode": "immediate"}], "label": f.name, "method": "animate"} for f in lt_frames],
                "x": 0.05, "len": 0.9, "y": -0.05,
                "currentvalue": {"prefix": "Lap: ", "visible": True, "xanchor": "center"},
                "active": len(lt_frames) - 1,
            }],
        )
        st.plotly_chart(fig_lt, use_container_width=True)

    # Position changes in 2 columns below lap times
    if "GridPosition" in results.columns and "Position" in results.columns:
        st.divider()
        rc = results.copy()
        rc["GridPos"] = pd.to_numeric(rc["GridPosition"], errors="coerce")
        rc["FinishPos"] = pd.to_numeric(rc["Position"], errors="coerce")
        rc["Change"] = rc["GridPos"] - rc["FinishPos"]
        rc = rc.dropna(subset=["GridPos", "FinishPos", "Change", "Abbreviation"])
        rc = rc.sort_values("FinishPos")

        col_left, col_right = st.columns(2)

        with col_left:
            st.components.v1.html("""
<vega-font
  variant="font-h4"
  as="h4"
  style="font-weight: bold;"
>
  Positions Gained / Lost
</vega-font>
""", height=44)
            fig_changes = go.Figure(go.Bar(
                x=rc["Abbreviation"],
                y=rc["Change"],
                marker_color=["#2ecc71" if c > 0 else "#e74c3c" if c < 0 else "#95a5a6" for c in rc["Change"]],
                text=[f"+{int(c)}" if c > 0 else str(int(c)) if c != 0 else "—" for c in rc["Change"]],
                textposition="outside",
            ))
            fig_changes.update_layout(
                xaxis_title="Driver",
                yaxis_title="Positions",
                height=350,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(zeroline=True, zerolinecolor="#444"),
            )
            st.plotly_chart(fig_changes, use_container_width=True)

        with col_right:
            st.components.v1.html("""
<vega-font
  variant="font-h4"
  as="h4"
  style="font-weight: bold;"
>
  Grid vs Finish Position
</vega-font>
""", height=44)
            fig_grid = go.Figure()
            fig_grid.add_trace(go.Scatter(
                x=rc["GridPos"],
                y=rc["FinishPos"],
                mode="markers+text",
                text=rc["Abbreviation"],
                textposition="top center",
                marker=dict(
                    size=10,
                    color=rc["Change"],
                    colorscale="RdYlGn",
                    showscale=False,
                ),
            ))
            fig_grid.add_shape(type="line", x0=1, y0=1, x1=rc["GridPos"].max(), y1=rc["GridPos"].max(),
                               line=dict(color="#555", dash="dash"))
            fig_grid.update_layout(
                xaxis=dict(title="Grid Position", autorange="reversed"),
                yaxis=dict(title="Finish Position", autorange="reversed"),
                height=350,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_grid, use_container_width=True)

    st.divider()

    # Tyre strategy timeline
    st.components.v1.html("""
<vega-font
  variant="font-h4"
  as="h4"
  style="font-weight: bold;"
>
  Tyre Strategy
</vega-font>
""", height=44)
    strat = laps.dropna(subset=["Compound", "LapNumber"]).copy() if "Compound" in laps.columns else pd.DataFrame()
    if not strat.empty:
        fig_tyre = px.scatter(
            strat,
            x="LapNumber",
            y="Driver",
            color="Compound",
            color_discrete_map=COMPOUND_COLORS,
            labels={"LapNumber": "Lap", "Driver": "Driver"},
            height=max(400, len(strat["Driver"].unique()) * 22),
        )
        fig_tyre.update_traces(marker=dict(size=7, symbol="square"))
        fig_tyre.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_tyre, use_container_width=True)


# ── QUALIFYING ────────────────────────────────────────────────────────────────
else:
    pole = results.iloc[0]
    vega_metrics([
        {"label": "Pole Position", "value": pole.get("Abbreviation", "—")},
        {"label": "Team", "value": pole.get("TeamName", "—")},
    ])
    st.divider()

    # Q1 / Q2 / Q3 gap-to-pole horizontal bar charts
    for q_col in ["Q3", "Q2", "Q1"]:
        if q_col not in results.columns:
            continue
        q_data = results[["Abbreviation", q_col]].dropna(subset=[q_col]).copy()
        if q_data.empty:
            continue
        q_data["Seconds"] = q_data[q_col].apply(
            lambda t: t.total_seconds() if hasattr(t, "total_seconds") else None
        )
        q_data = q_data.dropna(subset=["Seconds"]).sort_values("Seconds")
        if q_data.empty:
            continue

        pole_time = q_data["Seconds"].min()
        q_data["Gap"] = q_data["Seconds"] - pole_time
        q_data["Label"] = q_data["Gap"].apply(lambda g: "POLE" if g == 0 else f"+{g:.3f}s")

        st.components.v1.html(f"""
<vega-font
  variant="font-h4"
  as="h4"
  style="font-weight: bold;"
>
  {q_col} — Gap to Pole
</vega-font>
""", height=30)
        fig_q = px.bar(
            q_data,
            x="Gap",
            y="Abbreviation",
            orientation="h",
            text="Label",
            color="Gap",
            color_continuous_scale="RdYlGn_r",
            labels={"Gap": "Gap to Pole (s)", "Abbreviation": "Driver"},
            height=max(300, len(q_data) * 28),
        )
        fig_q.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
        )
        fig_q.update_traces(textposition="outside")
        st.plotly_chart(fig_q, use_container_width=True)
        st.divider()

# Footer with country flag
st.divider()
render_footer()
