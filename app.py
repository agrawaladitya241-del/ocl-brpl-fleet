"""
app.py — OCL/BRPL Fleet Intelligence Dashboard
-----------------------------------------------
Seven tabs:
  1. Overview
  2. Vehicles
  3. Groups
  4. Routes
  5. Accident Vehicles
  6. Audit / Verify
  7. Raw Data

Locked to April 2026 data format.
Reads only the OCL and BRPL sheets; everything else is ignored.
"""

from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import streamlit as st

import data_loader
import analytics

# ==================================================================
# Page config + theme
# ==================================================================

st.set_page_config(
    page_title="OCL/BRPL Fleet Intelligence",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================================================================
# Theme system — light by default, with toggle
# ==================================================================

if "theme" not in st.session_state:
    st.session_state["theme"] = "light"


def get_theme_palette(theme: str) -> dict:
    if theme == "dark":
        return {
            "bg":            "#0b0d10",
            "panel":         "#11141a",
            "border":        "#1f2328",
            "border_strong": "#2a3039",
            "text":          "#f5f5f5",
            "text_muted":    "#8b93a1",
            "text_dim":      "#6b7280",
            "h2":            "#e5e7eb",
            "h3":            "#9aa3b2",
            "sidebar_bg":    "#0f1216",
            "tab_active":    "#f59e0b",
            "alert_bg":      "#14181e",
            "note_text":     "#d1d5db",
            "accent_green":  "#22c55e",
            "accent_red":    "#ef4444",
            "accent_amber":  "#f59e0b",
            "accent_blue":   "#60a5fa",
            "accent_purple": "#a855f7",
            "chart_bg":      "#0b0d10",
            "chart_grid":    "#1f2328",
            "chart_text":    "#d1d5db",
            "chart_line":    "#60a5fa",
        }
    return {
        "bg":            "#ffffff",
        "panel":         "#ffffff",
        "border":        "#e5e7eb",
        "border_strong": "#cbd5e1",
        "text":          "#111827",
        "text_muted":    "#6b7280",
        "text_dim":      "#9ca3af",
        "h2":            "#1f2937",
        "h3":            "#6b7280",
        "sidebar_bg":    "#f9fafb",
        "tab_active":    "#d97706",
        "alert_bg":      "#f9fafb",
        "note_text":     "#374151",
        "accent_green":  "#15803d",
        "accent_red":    "#b91c1c",
        "accent_amber":  "#b45309",
        "accent_blue":   "#1d4ed8",
        "accent_purple": "#6d28d9",
        "chart_bg":      "#ffffff",
        "chart_grid":    "#e5e7eb",
        "chart_text":    "#374151",
        "chart_line":    "#1d4ed8",
    }


def make_css(p: dict) -> str:
    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

  html, body, [class*="css"] {{ font-family: 'IBM Plex Sans', -apple-system, sans-serif !important; }}
  .stApp {{ background: {p['bg']}; }}

  .block-container {{
    padding-top: 1.75rem;
    padding-bottom: 4rem;
    max-width: 1500px;
  }}

  h1, h2, h3, h4 {{ font-family: 'IBM Plex Sans', sans-serif !important; letter-spacing: -0.01em; color: {p['text']}; }}
  h1 {{
    font-weight: 700;
    font-size: 1.9rem !important;
    border-bottom: 1px solid {p['border']};
    padding-bottom: 0.75rem;
    margin-bottom: 0.25rem !important;
  }}
  h2 {{ font-weight: 600; font-size: 1.15rem !important; margin-top: 1.8rem !important; color: {p['h2']}; }}
  h3 {{
    font-weight: 500; font-size: 0.85rem !important; color: {p['h3']};
    text-transform: uppercase; letter-spacing: 0.08em;
    margin-top: 1rem !important; margin-bottom: 0.5rem !important;
  }}

  p, span, div, label {{ color: {p['text']}; }}

  .page-subtitle {{ color: {p['text_muted']}; font-size: 0.9rem; margin-bottom: 1.5rem; font-weight: 400; }}

  .kpi-card {{ background: {p['panel']}; border: 1px solid {p['border']}; border-radius: 6px; padding: 1.1rem 1.25rem; height: 100%; }}
  .kpi-label {{ color: {p['text_muted']}; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }}
  .kpi-value {{ font-family: 'JetBrains Mono', monospace; font-size: 2rem; font-weight: 700; color: {p['text']}; line-height: 1; }}
  .kpi-unit {{ color: {p['text_muted']}; font-size: 0.95rem; font-weight: 400; margin-left: 0.25rem; }}
  .kpi-sub {{ color: {p['text_dim']}; font-size: 0.75rem; margin-top: 0.4rem; }}
  .kpi-card.accent-green .kpi-value {{ color: {p['accent_green']}; }}
  .kpi-card.accent-red   .kpi-value {{ color: {p['accent_red']}; }}
  .kpi-card.accent-amber .kpi-value {{ color: {p['accent_amber']}; }}
  .kpi-card.accent-blue  .kpi-value {{ color: {p['accent_blue']}; }}
  .kpi-card.accent-purple .kpi-value {{ color: {p['accent_purple']}; }}

  section[data-testid="stSidebar"] {{ background: {p['sidebar_bg']}; border-right: 1px solid {p['border']}; }}
  section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {{ color: {p['h2']}; }}
  section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p {{ color: {p['text']}; }}

  /* ---- Input widgets (selectbox, multiselect, number_input, text_input) ---- */
  div[data-baseweb="select"] > div {{
    background-color: {p['panel']} !important;
    border-color: {p['border']} !important;
    color: {p['text']} !important;
  }}
  div[data-baseweb="select"] span,
  div[data-baseweb="select"] input {{
    color: {p['text']} !important;
  }}
  div[data-baseweb="popover"] ul,
  div[data-baseweb="popover"] li {{
    background-color: {p['panel']} !important;
    color: {p['text']} !important;
  }}
  div[data-baseweb="popover"] li:hover {{
    background-color: {p['alert_bg']} !important;
  }}
  span[data-baseweb="tag"] {{
    background-color: {p['accent_blue']} !important;
    color: #ffffff !important;
  }}
  input[type="number"], input[type="text"],
  div[data-baseweb="input"] input,
  div[data-baseweb="base-input"] input {{
    background-color: {p['panel']} !important;
    color: {p['text']} !important;
    border-color: {p['border']} !important;
  }}
  div[data-baseweb="input"], div[data-baseweb="base-input"] {{
    background-color: {p['panel']} !important;
    border-color: {p['border']} !important;
  }}
  button[data-testid="stNumberInputStepDown"],
  button[data-testid="stNumberInputStepUp"] {{
    background-color: {p['panel']} !important;
    color: {p['text']} !important;
    border-color: {p['border']} !important;
  }}
  div[data-baseweb="calendar"] {{
    background-color: {p['panel']} !important;
    color: {p['text']} !important;
  }}
  div[data-testid="stButton"] > button {{
    background-color: {p['panel']} !important;
    color: {p['text']} !important;
    border: 1px solid {p['border']} !important;
  }}
  div[data-testid="stButton"] > button:hover {{
    border-color: {p['accent_blue']} !important;
    color: {p['accent_blue']} !important;
  }}
  label[data-baseweb="checkbox"] span,
  label[data-baseweb="radio"] span {{
    color: {p['text']} !important;
  }}

  .stTabs [data-baseweb="tab-list"] {{ gap: 0; border-bottom: 1px solid {p['border']}; overflow-x: auto; }}
  .stTabs [data-baseweb="tab"] {{ background: transparent; color: {p['text_muted']}; font-weight: 500; padding: 0.65rem 1.1rem; border: none; border-bottom: 2px solid transparent; white-space: nowrap; }}
  .stTabs [aria-selected="true"] {{ color: {p['text']} !important; border-bottom: 2px solid {p['tab_active']} !important; background: transparent !important; }}

  .stDataFrame {{ border: 1px solid {p['border']}; border-radius: 6px; }}
  [data-testid="stFileUploader"] section {{ background: {p['panel']}; border: 1px dashed {p['border_strong']}; border-radius: 6px; }}
  .stAlert {{ background: {p['alert_bg']}; border: 1px solid {p['border']}; border-radius: 6px; }}

  footer {{ visibility: hidden; }}
  header[data-testid="stHeader"] {{ background: transparent; }}

  .note-box {{ background: {p['alert_bg']}; border: 1px solid {p['border']}; border-left: 3px solid {p['accent_amber']}; padding: 0.6rem 0.9rem; border-radius: 3px; color: {p['note_text']}; font-size: 0.85rem; margin: 0.5rem 0; }}
  .note-box.info    {{ border-left-color: {p['accent_blue']}; }}
  .note-box.success {{ border-left-color: {p['accent_green']}; }}
  .note-box.danger  {{ border-left-color: {p['accent_red']}; }}
</style>
"""


PALETTE = get_theme_palette(st.session_state["theme"])
st.markdown(make_css(PALETTE), unsafe_allow_html=True)


def kpi_card(label: str, value, unit: str = "", sub: str = "", accent: str = "") -> str:
    accent_cls = f"accent-{accent}" if accent else ""
    unit_html = f'<span class="kpi-unit">{unit}</span>' if unit else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card {accent_cls}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}{unit_html}</div>
      {sub_html}
    </div>
    """


def note(msg: str, kind: str = "info"):
    st.markdown(f'<div class="note-box {kind}">{msg}</div>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_data(file_bytes: bytes, month: int, year: int):
    buf = io.BytesIO(file_bytes)
    df = data_loader.load_all(buf, month=month, year=year)
    if df.empty:
        return df
    return analytics.add_status_column(df)


# ==================================================================
# Header
# ==================================================================

st.markdown("# OCL / BRPL Fleet Intelligence")
st.markdown(
    '<div class="page-subtitle">Contractor fleet dashboard · Tipper trailer operations · April 2026</div>',
    unsafe_allow_html=True,
)

# ==================================================================
# Sidebar: upload + controls
# ==================================================================

with st.sidebar:
    # Theme toggle
    theme_label = "🌙 Switch to dark mode" if st.session_state["theme"] == "light" else "☀ Switch to light mode"
    if st.button(theme_label, key="theme_toggle", use_container_width=True):
        st.session_state["theme"] = "dark" if st.session_state["theme"] == "light" else "light"
        st.rerun()

    st.markdown("### Data")
    uploaded = st.file_uploader(
        "Upload OCL/BRPL report (.xlsx)",
        type=["xlsx"],
        help="Workbook with 'OCL' and 'BRPL' sheets. Other sheets are ignored.",
    )
    month_name_to_num = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                         "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}
    selected_month_name = st.selectbox("Month", list(month_name_to_num.keys()), index=3)  # default April
    year_pick = st.number_input("Year", min_value=2020, max_value=2100, value=2026)

if not uploaded:
    st.info(
        "Upload a fleet report Excel file to begin. Expected format: "
        "one 'OCL' sheet and one 'BRPL' sheet, each with a row per vehicle and "
        "numbered day columns (1, 2, 3...)."
    )
    st.stop()

file_bytes = uploaded.getvalue()

with st.spinner("Loading workbook…"):
    try:
        df_all = load_data(file_bytes, month_name_to_num[selected_month_name], int(year_pick))
    except Exception as e:
        st.error(f"Couldn't read that file: {e}")
        st.stop()

if df_all.empty:
    st.warning(
        "No data found. Make sure your file has sheets named 'OCL' and/or 'BRPL' "
        "with a header row containing 'V NO' (or similar) and numbered day columns."
    )
    st.stop()

# ==================================================================
# Sidebar: filters
# ==================================================================

with st.sidebar:
    st.markdown("### Filters")
    contractor_options = ["Both"] + sorted(df_all["contractor"].unique().tolist())
    selected_contractor = st.selectbox("Contractor", contractor_options, index=0)

    all_groups = sorted([g for g in df_all["group"].unique() if g and str(g).strip()])
    group_filter = st.multiselect("Group", all_groups)

    all_vehicles = sorted(df_all["vehicle"].unique())
    vehicle_filter = st.multiselect("Vehicle", all_vehicles)

# Apply filters
df = df_all.copy()
if selected_contractor != "Both":
    df = df[df["contractor"] == selected_contractor]
if group_filter:
    df = df[df["group"].isin(group_filter)]
if vehicle_filter:
    df = df[df["vehicle"].isin(vehicle_filter)]

if df.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

# ==================================================================
# KPIs
# ==================================================================

kpis = analytics.compute_kpis(df)
latest = kpis["latest_date"]
latest_str = latest.strftime("%d %b %Y") if latest is not None else "—"

st.markdown(
    f"<div style='color:#8b93a1; font-size:0.85rem; margin-bottom:1rem;'>"
    f"Contractor: <strong style='color:#d1d5db;'>{selected_contractor}</strong> · "
    f"Month: <strong style='color:#d1d5db;'>{selected_month_name} {int(year_pick)}</strong> · "
    f"Latest day: <strong style='color:#d1d5db;'>{latest_str}</strong> · "
    f"Vehicles: <strong style='color:#d1d5db;'>{kpis['total_vehicles']}</strong>"
    f"</div>",
    unsafe_allow_html=True,
)

st.markdown("### Top-line metrics")
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(kpi_card("Total trips", f"{kpis['total_trips_month']:,}", accent="green",
                         sub="highlighted cells = routes"), unsafe_allow_html=True)
with k2:
    st.markdown(kpi_card("Avg days / trip", kpis["avg_days_per_trip"], accent="blue",
                         sub="working days ÷ trips"), unsafe_allow_html=True)
with k3:
    st.markdown(kpi_card("Fleet utilization", kpis["fleet_util_pct"], unit="%", accent="blue",
                         sub="excl. accident, DP, R&M"), unsafe_allow_html=True)
with k4:
    st.markdown(kpi_card("Accident vehicles", kpis["accident_vehicles"], accent="purple",
                         sub="grounded for month"), unsafe_allow_html=True)
with k5:
    st.markdown(kpi_card("Active trips today", kpis["active_trips"], accent="green",
                         sub=f"of {kpis['total_vehicles']} vehicles"), unsafe_allow_html=True)

st.markdown("### Day breakdown for this period")
d1, d2, d3, d4 = st.columns(4)
with d1:
    st.markdown(
        kpi_card("DH days", kpis["dh_days_month"], accent="red",
                 sub="Driver Home (total this month)"),
        unsafe_allow_html=True,
    )
with d2:
    st.markdown(
        kpi_card("DP days", kpis["dp_days_month"], accent="red",
                 sub="Driver Problem (total this month)"),
        unsafe_allow_html=True,
    )
with d3:
    st.markdown(
        kpi_card("R&M days", kpis["rm_days_month"], accent="purple",
                 sub="Repair & Maintenance (total this month)"),
        unsafe_allow_html=True,
    )
with d4:
    st.markdown(
        kpi_card("No-data days", kpis["no_data_days_month"], accent="amber",
                 sub="blank cells (no entry)"),
        unsafe_allow_html=True,
    )

# Data quality warnings
warnings = analytics.data_quality_warnings(df_all)
if warnings:
    with st.expander(f"Data quality notes ({len(warnings)})", expanded=False):
        for w in warnings:
            st.markdown(f"- {w}")

# ==================================================================
# Tabs
# ==================================================================

tab_over, tab_veh, tab_grp, tab_routes, tab_acc, tab_audit, tab_raw = st.tabs(
    ["Overview", "Vehicles", "Groups", "Routes", "Accident Vehicles", "Audit / Verify", "Raw Data"]
)

# ---------- Overview ----------
with tab_over:
    st.markdown("## Daily status distribution")
    ds = analytics.daily_summary(df)
    if ds.empty:
        note("Not enough data to chart.", "info")
    else:
        status_cols = [c for c in analytics.STATUS_ORDER if c != "NO_DATA"]
        melted = ds.melt(id_vars=["date"], value_vars=status_cols, var_name="status", value_name="count")
        fig = px.bar(
            melted, x="date", y="count", color="status",
            color_discrete_map=analytics.STATUS_COLORS,
            category_orders={"status": status_cols},
            labels={"date": "", "count": "Vehicles", "status": "Status"},
        )
        fig.update_layout(
            plot_bgcolor=PALETTE["chart_bg"], paper_bgcolor=PALETTE["chart_bg"],
            font=dict(family="IBM Plex Sans", color=PALETTE["chart_text"]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=20, r=20, t=40, b=20), height=420,
            xaxis=dict(gridcolor=PALETTE["chart_grid"], showgrid=False),
            yaxis=dict(gridcolor=PALETTE["chart_grid"]),
            bargap=0.15,
        )
        for t in fig.data:
            t.name = analytics.STATUS_LABELS.get(t.name, t.name)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("## Utilization trend")
        fig2 = px.line(ds, x="date", y="utilization_pct", markers=True,
                       labels={"date": "", "utilization_pct": "Utilization %"})
        fig2.update_traces(line_color=PALETTE["chart_line"], marker=dict(size=6))
        fig2.update_layout(
            plot_bgcolor=PALETTE["chart_bg"], paper_bgcolor=PALETTE["chart_bg"],
            font=dict(family="IBM Plex Sans", color=PALETTE["chart_text"]),
            margin=dict(l=20, r=20, t=20, b=20), height=260,
            xaxis=dict(gridcolor=PALETTE["chart_grid"], showgrid=False),
            yaxis=dict(gridcolor=PALETTE["chart_grid"], range=[0, 105]),
        )
        st.plotly_chart(fig2, use_container_width=True)

# ---------- Vehicles ----------
with tab_veh:
    vs = analytics.vehicle_summary(df)
    if vs.empty:
        note("No vehicle data.", "info")
    else:
        has_manual = vs["trips_manual"].notna().any()
        if has_manual:
            note(
                "<strong>trips_manual</strong> = Excel Trip column (if present). "
                "<strong>trips_computed</strong> = our count of highlighted cells. "
                "Compare the two to verify accuracy.",
                "info",
            )
        else:
            note(
                "No manual Trip column in this view. <strong>trips_computed</strong> uses the "
                "highlighted-cell rule — every highlighted (blue) cell is counted as one trip.",
                "info",
            )

        st.markdown("## Top performers")
        top = vs.dropna(subset=["utilization_pct"]).head(10)
        st.dataframe(
            top, use_container_width=True, hide_index=True,
            column_config={
                "utilization_pct": st.column_config.ProgressColumn(
                    "Utilization %", min_value=0, max_value=100, format="%.1f%%"),
                "is_accident_vehicle": st.column_config.CheckboxColumn("Accident"),
            },
        )

        st.markdown("## Flagged vehicles")
        note("Vehicles with <strong>utilization &lt; 40%</strong>, <strong>DH ≥ 3 days</strong>, or <strong>DP ≥ 2 days</strong>. Worth manager follow-up.", "danger")
        flagged = vs[
            ((vs["utilization_pct"] < 40) & vs["utilization_pct"].notna())
            | (vs["DH"] >= 3) | (vs["DP"] >= 2)
        ].sort_values("utilization_pct", na_position="first")
        if flagged.empty:
            note("No vehicles flagged.", "success")
        else:
            st.dataframe(
                flagged, use_container_width=True, hide_index=True,
                column_config={
                    "utilization_pct": st.column_config.ProgressColumn(
                        "Utilization %", min_value=0, max_value=100, format="%.1f%%"),
                    "is_accident_vehicle": st.column_config.CheckboxColumn("Accident"),
                },
            )

        st.markdown("## Day breakdown per vehicle")
        note(
            "Vehicles broken down by their unproductive day counts. "
            "<strong>DH</strong> = Driver Home · <strong>DP</strong> = Driver Problem · "
            "<strong>RM</strong> = Repair & Maintenance.",
            "info",
        )

        col_dh, col_dp, col_rm = st.columns(3)

        with col_dh:
            st.markdown("### Driver Home (DH)")
            dh_df = analytics.vehicles_with_dh(df)
            if dh_df.empty:
                note("No DH days in this view.", "success")
            else:
                dh_disp = dh_df.copy()
                dh_disp["first_dh"] = dh_disp["first_dh"].dt.strftime("%d %b")
                dh_disp["last_dh"] = dh_disp["last_dh"].dt.strftime("%d %b")
                st.dataframe(dh_disp, use_container_width=True, hide_index=True)

        with col_dp:
            st.markdown("### Driver Problem (DP)")
            dp_df = analytics.vehicles_with_dp(df)
            if dp_df.empty:
                note("No DP days in this view.", "success")
            else:
                dp_disp = dp_df.copy()
                dp_disp["first_dp"] = dp_disp["first_dp"].dt.strftime("%d %b")
                dp_disp["last_dp"] = dp_disp["last_dp"].dt.strftime("%d %b")
                st.dataframe(dp_disp, use_container_width=True, hide_index=True)

        with col_rm:
            st.markdown("### Repair & Maintenance (RM)")
            rm_df = analytics.vehicles_with_rm(df)
            if rm_df.empty:
                note("No R&M days in this view.", "success")
            else:
                rm_disp = rm_df.copy()
                rm_disp["first_rm"] = rm_disp["first_rm"].dt.strftime("%d %b")
                rm_disp["last_rm"] = rm_disp["last_rm"].dt.strftime("%d %b")
                st.dataframe(rm_disp, use_container_width=True, hide_index=True)

        st.markdown("## All vehicles")
        st.dataframe(
            vs, use_container_width=True, hide_index=True,
            column_config={
                "utilization_pct": st.column_config.ProgressColumn(
                    "Utilization %", min_value=0, max_value=100, format="%.1f%%"),
                "is_accident_vehicle": st.column_config.CheckboxColumn("Accident"),
            },
        )

        st.markdown("## Vehicle drill-down")
        veh_to_inspect = st.selectbox(
            "Pick a vehicle to see its exact DH/DP days and full status history",
            options=sorted(vs["vehicle"].tolist()), key="veh_drill",
        )
        if veh_to_inspect:
            colA, colB = st.columns(2)
            with colA:
                st.markdown("### DH (Driver Home) days")
                dh_df = analytics.status_detail(df, veh_to_inspect, "DH")
                if dh_df.empty:
                    note("No DH days for this vehicle.", "success")
                else:
                    dh_df["date"] = dh_df["date"].dt.strftime("%d %b")
                    st.dataframe(dh_df, use_container_width=True, hide_index=True)
            with colB:
                st.markdown("### DP (Driver Problem) days")
                dp_df = analytics.status_detail(df, veh_to_inspect, "DP")
                if dp_df.empty:
                    note("No DP days for this vehicle.", "success")
                else:
                    dp_df["date"] = dp_df["date"].dt.strftime("%d %b")
                    st.dataframe(dp_df, use_container_width=True, hide_index=True)

            st.markdown("### Full status history for this vehicle")
            v_daily = df[df["vehicle"] == veh_to_inspect][
                ["date", "status", "status_raw", "is_highlighted", "contractor"]
            ].sort_values("date")
            v_daily["date"] = v_daily["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(v_daily, use_container_width=True, hide_index=True, height=350)

# ---------- Groups ----------
with tab_grp:
    gs = analytics.group_summary(df)
    if gs.empty:
        note("No group data.", "info")
    else:
        st.markdown("## Group performance")
        note(
            "Each row is a GROUP (BRPL, CNG, KOIRA, OCL, etc.) — "
            "the logistics lane / contract assignment from the Excel GROUP column.",
            "info",
        )
        st.dataframe(
            gs, use_container_width=True, hide_index=True,
            column_config={
                "utilization_pct": st.column_config.ProgressColumn(
                    "Utilization %", min_value=0, max_value=100, format="%.1f%%"),
            },
        )

# ---------- Routes ----------
with tab_routes:
    rs = analytics.route_summary(df)
    if rs.empty:
        note(
            "No routes detected. Routes are cells highlighted in blue (route marker) "
            "or cells matching an ORIGIN-DESTINATION pattern.",
            "info",
        )
    else:
        st.markdown("## Route summary")
        note(
            "Each row is a unique route code. <strong>trip_count</strong> = how many times that "
            "route was logged across all vehicles. Routes are identified by blue highlighting "
            "in the Excel file.",
            "info",
        )
        st.dataframe(rs, use_container_width=True, hide_index=True)

        st.markdown("## Route details")
        route_pick = st.selectbox("Route", options=rs["route"].tolist(), key="route_pick")
        if route_pick:
            route_cells = df[
                (df["status"] == "TRIP")
                & (df["status_raw"].str.upper().str.replace(r"\s+", "", regex=True) == route_pick)
            ].copy()
            if route_cells.empty:
                note("No cells for this route.", "info")
            else:
                st.markdown(f"### {len(route_cells)} trip(s) on route {route_pick}")
                route_cells["date"] = route_cells["date"].dt.strftime("%Y-%m-%d")
                st.dataframe(
                    route_cells[["date", "vehicle", "contractor", "group", "status_raw", "is_highlighted"]],
                    use_container_width=True, hide_index=True, height=400,
                )

                st.markdown("### Trips by vehicle on this route")
                by_veh = (
                    route_cells.groupby("vehicle").size().reset_index(name="trip_count")
                    .sort_values("trip_count", ascending=False)
                )
                st.dataframe(by_veh, use_container_width=True, hide_index=True)

# ---------- Accident Vehicles ----------
with tab_acc:
    st.markdown("## Accident-grounded vehicles")
    acc = analytics.identify_accident_vehicles(df)
    if acc.empty:
        note("No accident-grounded vehicles in this view.", "success")
    else:
        note(
            f"Found <strong>{len(acc)} vehicle(s)</strong> with 3+ days marked with "
            "<strong>ACC</strong>, <strong>accident</strong>, or related keywords "
            "(cabin damage, breakdown, etc.). Excluded from fleet utilization.",
            "danger",
        )
        acc_display = acc.copy()
        acc_display["first_date"] = acc_display["first_date"].dt.strftime("%d %b %Y")
        acc_display["last_date"] = acc_display["last_date"].dt.strftime("%d %b %Y")
        st.dataframe(acc_display, use_container_width=True, hide_index=True)

# ---------- Audit / Verify ----------
with tab_audit:
    st.markdown("## Search (Excel Find equivalent)")
    st.markdown(
        "Type any text and see every matching cell. Use this to verify counts against the Excel file."
    )
    q_col1, q_col2 = st.columns([4, 1])
    with q_col1:
        query = st.text_input("Search text", placeholder="e.g. DH, ACC, LPD, B-M, D-SMC")
    with q_col2:
        case_sensitive = st.checkbox("Case-sensitive", value=False)

    scope = st.radio("Search scope", ["Current view", "All data"], horizontal=True, key="search_scope")
    scope_df = df if scope == "Current view" else df_all

    if query:
        results = analytics.search_cells(scope_df, query, case_sensitive=case_sensitive)
        if results.empty:
            note(f"No cells found matching '{query}'.", "info")
        else:
            st.markdown(f"### {len(results)} match(es)")
            results["date"] = results["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(results, use_container_width=True, hide_index=True, height=400)

    st.divider()
    st.markdown("## Count verification")
    st.markdown(
        "Pick any status to see every cell classified that way. This lets you cross-check our "
        "counts against the Excel file. The OTHER status shows codes we couldn't classify."
    )
    status_to_audit = st.selectbox(
        "Status to audit",
        options=[s for s in analytics.STATUS_ORDER if s != "NO_DATA"],
        format_func=lambda s: f"{s} — {analytics.STATUS_LABELS.get(s, s)}",
    )
    if status_to_audit:
        audit_df = df[df["status"] == status_to_audit].copy()
        st.markdown(f"### {len(audit_df)} cell(s) classified as {status_to_audit}")
        if status_to_audit == "OTHER" and not audit_df.empty:
            note(
                "These codes don't match known patterns (LP*, MT*, RM, LRM, DH, DP, ACC, TNST, ULP) "
                "and aren't highlighted as routes. Send me the unique codes and I'll update the classifier.",
                "info",
            )
        if not audit_df.empty:
            audit_display = audit_df[["date", "vehicle", "contractor", "group", "status_raw"]].copy()
            audit_display["date"] = audit_display["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(audit_display, use_container_width=True, hide_index=True, height=400)

            csv_bytes = audit_display.to_csv(index=False).encode("utf-8")
            st.download_button(
                f"Download {status_to_audit} audit CSV",
                data=csv_bytes,
                file_name=f"audit_{status_to_audit.lower()}.csv",
                mime="text/csv",
            )

# ---------- Raw Data ----------
with tab_raw:
    st.markdown("## Daily log")
    st.markdown("One row per vehicle per day. Filter with the sidebar. Download as CSV.")
    display_df = df[[
        "date", "vehicle", "contractor", "group", "status", "status_raw",
        "is_highlighted", "location_text", "manual_trip_count"
    ]].copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    display_df = display_df.rename(columns={
        "status_raw": "original_code", "is_highlighted": "highlighted_route",
        "location_text": "last_location", "manual_trip_count": "excel_trip_count",
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)

    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV", data=csv_bytes,
        file_name=f"ocl_brpl_log_{selected_month_name.lower()}_{int(year_pick)}.csv",
        mime="text/csv",
    )
