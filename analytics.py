"""
analytics.py  —  OCL/BRPL classification + summaries
-----------------------------------------------------
Status taxonomy (confirmed with user):
  TRIP     - Active laden trip (highlighted cell OR route pattern X-Y)
  ULP      - Unloading Point
  TNST     - In Transit
  LP_*     - Loading Point at location X (any code starting with LP)
  MT_*     - Empty Truck Movement (any code starting with MT)
  RM       - Raw Material (loaded)
  LRM      - Loading Raw Material
  DH       - Driver Home
  DP       - Driver Problem
  ACCIDENT - Vehicle grounded (ACC, accident, cabin damage, etc.)
  OTHER    - Doesn't match any known pattern (flagged for manual review)
  NO_DATA  - Empty cell
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

import pandas as pd


# ----------------------------------------------------------------------
# Classification patterns
# ----------------------------------------------------------------------

# Accident-related keywords in either the cell or related text
_RE_ACCIDENT = re.compile(
    r"\bACC\b|accident|cabin\s*damage|engine\s*fail|breakdown|break\s*down",
    re.IGNORECASE,
)
_RE_DH = re.compile(r"^\s*DH\d*\s*$|\(DH\)", re.IGNORECASE)
_RE_DP = re.compile(r"^\s*DP\d*\s*$|\(DP\)", re.IGNORECASE)
_RE_ULP = re.compile(r"^\s*ULP\b", re.IGNORECASE)
_RE_TNST = re.compile(r"^\s*TNST\s*$", re.IGNORECASE)
_RE_RM = re.compile(r"^\s*RM\d*\s*$", re.IGNORECASE)         # RM or RM1 = Repair & Maintenance
_RE_LRM = re.compile(r"^\s*LRM\b", re.IGNORECASE)
_RE_LP = re.compile(r"^\s*LP[A-Z]*\b", re.IGNORECASE)          # LPD, LPB, LPOCL, LP OCL, etc.
_RE_MT = re.compile(r"^\s*MT[\s_]*[A-Z]*\b", re.IGNORECASE)    # MTO, MTOCL, MT OCL, MT ARUHA
# Route pattern: any ORIGIN-DEST with a hyphen (D-SMC, B-M, OCL-DCL, TSM-TSK, TSM-TSK/M)
_RE_ROUTE = re.compile(r"^\s*[A-Z][A-Z0-9]*\s*[-]\s*[A-Z][A-Z0-9/]*", re.IGNORECASE)


STATUS_ORDER = [
    "ACCIDENT", "DH", "DP", "LP", "RM", "LRM",
    "TNST", "ULP", "MT", "TRIP", "OTHER", "NO_DATA",
]

STATUS_LABELS = {
    "ACCIDENT": "Accident / Grounded",
    "DH": "Driver Home",
    "DP": "Driver Problem",
    "LP": "Loading Point",
    "RM": "Repair & Maintenance",
    "LRM": "Loading Raw Material",
    "TNST": "In Transit",
    "ULP": "Unloading Point",
    "MT": "Empty Movement",
    "TRIP": "Active Trip",
    "OTHER": "Other (uncategorized)",
    "NO_DATA": "No Data",
}

STATUS_COLORS = {
    "TRIP": "#22c55e",
    "ULP": "#16a34a",
    "TNST": "#eab308",
    "LP": "#f59e0b",
    "RM": "#a855f7",        # purple — unproductive (repair)
    "LRM": "#a3e635",       # light green — productive (loading raw material)
    "MT": "#fbbf24",
    "DH": "#ef4444",
    "DP": "#dc2626",
    "ACCIDENT": "#7c3aed",
    "OTHER": "#64748b",
    "NO_DATA": "#4b5563",
}


def classify_status(cell: str, is_highlighted: bool = False) -> str:
    """
    Classify one status cell.

    Precedence:
      1. NO_DATA if empty
      2. ACCIDENT if ACC or accident-related text
      3. DH / DP
      4. LRM  (must come before LP to avoid matching LRM as LP)
      5. LP*
      6. MT*
      7. RM
      8. TNST
      9. ULP
      10. TRIP if highlighted OR if matches route pattern X-Y
      11. OTHER
    """
    if cell is None:
        return "NO_DATA"
    text = str(cell).strip()
    if not text:
        return "NO_DATA"

    if _RE_ACCIDENT.search(text):
        return "ACCIDENT"
    if _RE_DH.search(text):
        return "DH"
    if _RE_DP.search(text):
        return "DP"
    if _RE_LRM.match(text):
        return "LRM"
    if _RE_LP.match(text):
        return "LP"
    if _RE_MT.match(text):
        return "MT"
    if _RE_RM.match(text):
        return "RM"
    if _RE_TNST.match(text):
        return "TNST"
    if _RE_ULP.match(text):
        return "ULP"
    # Highlighted cells are routes regardless of their text shape
    if is_highlighted:
        return "TRIP"
    # Text that looks like X-Y pattern even if not highlighted
    if _RE_ROUTE.match(text):
        return "TRIP"

    return "OTHER"


def add_status_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'status' column to the DataFrame."""
    out = df.copy()
    out["status"] = out.apply(
        lambda r: classify_status(r["status_raw"], r.get("is_highlighted", False)),
        axis=1,
    )
    return out


# ----------------------------------------------------------------------
# Trip counting and utilization
# ----------------------------------------------------------------------

PRODUCTIVE_STATES = {"TRIP", "ULP", "TNST", "LP", "MT", "LRM"}
# Days excluded from the working-day denominator entirely (truck isn't "at work" on these days):
EXCLUDED_FROM_DENOM = {"NO_DATA", "ACCIDENT", "DP", "RM"}


def trip_count_per_vehicle(df: pd.DataFrame) -> pd.Series:
    """Count trips per vehicle (highlighted cells)."""
    if "is_highlighted" not in df.columns:
        return pd.Series(dtype=int)
    return df.groupby("vehicle")["is_highlighted"].sum().astype(int)


# ----------------------------------------------------------------------
# Summaries
# ----------------------------------------------------------------------

def vehicle_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per vehicle with counts for each status + utilization %."""
    if df.empty:
        return pd.DataFrame()

    df = df if "status" in df.columns else add_status_column(df)

    pivot = (
        df.pivot_table(
            index="vehicle",
            columns="status",
            values="date",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    for s in STATUS_ORDER:
        if s not in pivot.columns:
            pivot[s] = 0

    # Trip count via highlighting
    trips = trip_count_per_vehicle(df).to_dict()
    pivot["trips_computed"] = pivot["vehicle"].map(trips).fillna(0).astype(int)

    # Manual trip count from Excel (if present)
    manual = (
        df[df["manual_trip_count"].notna()]
        .groupby("vehicle")["manual_trip_count"].max()
    )
    pivot["trips_manual"] = pivot["vehicle"].map(manual)

    # Contractor & group (first non-empty for that vehicle)
    contractor_map = df.groupby("vehicle")["contractor"].first()
    group_map = (
        df[df["group"].astype(str).str.strip() != ""]
        .groupby("vehicle")["group"].first()
    )
    location_map = (
        df[df["location_text"].astype(str).str.strip() != ""]
        .groupby("vehicle")["location_text"].first()
    )
    pivot["contractor"] = pivot["vehicle"].map(contractor_map).fillna("")
    pivot["group"] = pivot["vehicle"].map(group_map).fillna("")
    pivot["last_location"] = pivot["vehicle"].map(location_map).fillna("")

    # Accident flag — vehicle is flagged if >= 3 days ACCIDENT
    pivot["is_accident_vehicle"] = pivot["ACCIDENT"] >= 3

    # Utilization
    count_cols = [c for c in STATUS_ORDER if c not in EXCLUDED_FROM_DENOM]
    pivot["active_days"] = pivot[count_cols].sum(axis=1)
    pivot["productive_days"] = pivot[list(PRODUCTIVE_STATES)].sum(axis=1)
    pivot["utilization_pct"] = (
        (pivot["productive_days"] / pivot["active_days"].replace(0, pd.NA) * 100)
        .fillna(0)
        .round(1)
    )
    # Blank out utilization for accident vehicles
    pivot.loc[pivot["is_accident_vehicle"], "utilization_pct"] = None

    # Average days per trip (per vehicle): working_days / trips
    # working_days = active_days (already excludes NO_DATA, ACCIDENT, DP, RM)
    # Use manual trip count if available, else computed
    trip_for_avg = pivot["trips_manual"].fillna(pivot["trips_computed"])
    pivot["avg_days_per_trip"] = (
        pivot["active_days"] / trip_for_avg.replace(0, pd.NA)
    ).round(2)

    ordered = (
        ["vehicle", "contractor", "group", "is_accident_vehicle", "last_location"]
        + STATUS_ORDER
        + ["trips_computed", "trips_manual", "active_days", "productive_days",
           "utilization_pct", "avg_days_per_trip"]
    )
    pivot = pivot[ordered]
    return pivot.sort_values(
        by=["is_accident_vehicle", "utilization_pct"],
        ascending=[True, False],
        na_position="last",
    ).reset_index(drop=True)


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    df = df if "status" in df.columns else add_status_column(df)
    pivot = (
        df.pivot_table(
            index="date",
            columns="status",
            values="vehicle",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    for s in STATUS_ORDER:
        if s not in pivot.columns:
            pivot[s] = 0
    count_cols = [c for c in STATUS_ORDER if c not in EXCLUDED_FROM_DENOM]
    pivot["total_logged"] = pivot[count_cols].sum(axis=1)
    pivot["productive"] = pivot[list(PRODUCTIVE_STATES)].sum(axis=1)
    pivot["utilization_pct"] = (
        (pivot["productive"] / pivot["total_logged"].replace(0, pd.NA) * 100)
        .fillna(0)
        .round(1)
    )
    ordered = ["date"] + STATUS_ORDER + ["total_logged", "productive", "utilization_pct"]
    return pivot[ordered].sort_values("date").reset_index(drop=True)


def group_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per GROUP (BRPL, CNG, KOIRA, OCL, etc.) with aggregated metrics."""
    if df.empty:
        return pd.DataFrame()
    df = df if "status" in df.columns else add_status_column(df)
    df = df[df["group"].astype(str).str.strip() != ""]
    if df.empty:
        return pd.DataFrame()

    pivot = (
        df.pivot_table(
            index="group",
            columns="status",
            values="date",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    for s in STATUS_ORDER:
        if s not in pivot.columns:
            pivot[s] = 0

    pivot["vehicles"] = df.groupby("group")["vehicle"].nunique().values
    pivot["trips_computed"] = df.groupby("group")["is_highlighted"].sum().astype(int).values

    count_cols = [c for c in STATUS_ORDER if c not in EXCLUDED_FROM_DENOM]
    pivot["active_days"] = pivot[count_cols].sum(axis=1)
    pivot["productive_days"] = pivot[list(PRODUCTIVE_STATES)].sum(axis=1)
    pivot["utilization_pct"] = (
        (pivot["productive_days"] / pivot["active_days"].replace(0, pd.NA) * 100)
        .fillna(0)
        .round(1)
    )
    ordered = ["group", "vehicles"] + STATUS_ORDER + ["trips_computed", "active_days", "productive_days", "utilization_pct"]
    return pivot[ordered].sort_values("utilization_pct", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------
# KPIs
# ----------------------------------------------------------------------

def compute_kpis(df: pd.DataFrame) -> Dict:
    if df.empty:
        return {
            "total_vehicles": 0, "active_trips": 0, "drivers_home": 0,
            "drivers_problem": 0, "fleet_util_pct": 0.0,
            "accident_vehicles": 0, "latest_date": None,
            "total_trips_month": 0, "avg_days_per_trip": 0.0,
            "working_days_total": 0,
        }
    df = df if "status" in df.columns else add_status_column(df)
    latest_date = df["date"].max()
    latest = df[df["date"] == latest_date]

    total_vehicles = df["vehicle"].nunique()
    active_trips = int(latest["status"].isin(["TRIP", "ULP", "TNST"]).sum())
    drivers_home = int((latest["status"] == "DH").sum())
    drivers_problem = int((latest["status"] == "DP").sum())

    vs = vehicle_summary(df)
    accident_count = int(vs["is_accident_vehicle"].sum()) if not vs.empty else 0
    non_acc = vs[~vs["is_accident_vehicle"]] if not vs.empty else vs
    if not non_acc.empty and non_acc["active_days"].sum() > 0:
        fleet_util = round(
            non_acc["productive_days"].sum() / non_acc["active_days"].sum() * 100, 1
        )
    else:
        fleet_util = 0.0

    # Total trips: only use manual if EVERY vehicle has a manual count; else use computed.
    # This keeps the Total Trips KPI and Avg Days/Trip KPI consistent with each other.
    manual_total = df[df["manual_trip_count"].notna()].groupby("vehicle")["manual_trip_count"].max().sum()
    computed_total = int(df["is_highlighted"].sum())
    vehicles_in_view = df["vehicle"].unique()
    vehicles_with_manual = df[df["manual_trip_count"].notna()]["vehicle"].unique()
    all_have_manual = len(vehicles_with_manual) == len(vehicles_in_view) and manual_total > 0
    total_trips_month = int(manual_total) if all_have_manual else computed_total

    # Avg days per trip: working_days / total_trips (using the same trip count as above)
    working_days = int((~df["status"].isin(EXCLUDED_FROM_DENOM)).sum())
    avg_days_per_trip = round(working_days / total_trips_month, 2) if total_trips_month > 0 else 0.0

    return {
        "total_vehicles": total_vehicles,
        "active_trips": active_trips,
        "drivers_home": drivers_home,
        "drivers_problem": drivers_problem,
        "fleet_util_pct": fleet_util,
        "accident_vehicles": accident_count,
        "latest_date": latest_date,
        "total_trips_month": total_trips_month,
        "avg_days_per_trip": avg_days_per_trip,
        "working_days_total": working_days,
    }


# ----------------------------------------------------------------------
# Route analysis
# ----------------------------------------------------------------------

def route_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Count each unique route (using highlighted cells + matching X-Y patterns).
    Returns: route, trip_count, unique_vehicles
    """
    if df.empty:
        return pd.DataFrame()
    df = df if "status" in df.columns else add_status_column(df)
    trips = df[df["status"] == "TRIP"].copy()
    if trips.empty:
        return pd.DataFrame()
    # Normalize route text
    trips["route"] = trips["status_raw"].str.upper().str.replace(r"\s+", "", regex=True)
    agg = (
        trips.groupby("route")
        .agg(trip_count=("vehicle", "count"), unique_vehicles=("vehicle", "nunique"))
        .reset_index()
    )
    return agg.sort_values("trip_count", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------
# Accident vehicles
# ----------------------------------------------------------------------

def identify_accident_vehicles(df: pd.DataFrame, min_days: int = 3) -> pd.DataFrame:
    """Return vehicles with at least min_days ACCIDENT status."""
    df = df if "status" in df.columns else add_status_column(df)
    acc = df[df["status"] == "ACCIDENT"]
    if acc.empty:
        return pd.DataFrame(columns=["vehicle", "contractor", "group", "accident_days", "first_date", "last_date", "sample_text"])
    grouped = (
        acc.groupby("vehicle")
        .agg(
            contractor=("contractor", "first"),
            group=("group", "first"),
            accident_days=("date", "count"),
            first_date=("date", "min"),
            last_date=("date", "max"),
            sample_text=("status_raw", lambda s: s.iloc[0]),
        )
        .reset_index()
    )
    grouped = grouped[grouped["accident_days"] >= min_days]
    return grouped.sort_values("accident_days", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------
# Drill-down: exact days per vehicle for a given status
# ----------------------------------------------------------------------

def status_detail(df: pd.DataFrame, vehicle: str, status: str) -> pd.DataFrame:
    df = df if "status" in df.columns else add_status_column(df)
    sub = df[(df["vehicle"] == vehicle) & (df["status"] == status)].copy()
    return sub[["date", "status_raw", "contractor"]].sort_values("date").reset_index(drop=True)


# ----------------------------------------------------------------------
# Search
# ----------------------------------------------------------------------

def search_cells(df: pd.DataFrame, query: str, case_sensitive: bool = False) -> pd.DataFrame:
    if not query or not query.strip() or df.empty:
        return pd.DataFrame()
    q = query.strip()
    pattern = re.escape(q)
    if case_sensitive:
        mask = df["status_raw"].astype(str).str.contains(pattern, regex=True, na=False)
    else:
        mask = df["status_raw"].astype(str).str.contains(pattern, regex=True, case=False, na=False)
    sub = df[mask].copy()
    if sub.empty:
        return pd.DataFrame()
    return sub[["date", "vehicle", "contractor", "group", "status_raw"]].sort_values(
        ["date", "vehicle"]
    ).reset_index(drop=True)


# ----------------------------------------------------------------------
# Data quality warnings
# ----------------------------------------------------------------------

def data_quality_warnings(df: pd.DataFrame) -> List[str]:
    warnings = []
    if df.empty:
        return ["No data loaded."]

    df = df if "status" in df.columns else add_status_column(df)

    # Vehicles with many OTHER (uncategorized) cells
    other_per_vehicle = df[df["status"] == "OTHER"].groupby("vehicle").size()
    high_other = other_per_vehicle[other_per_vehicle >= 5]
    if len(high_other) > 0:
        warnings.append(
            f"⚠ {len(high_other)} vehicle(s) have 5+ uncategorized cells. "
            "Check the 'Audit / Verify' tab, filter by status = OTHER, to see the raw codes."
        )

    # Total OTHER cells (how much of the data couldn't be classified)
    other_total = (df["status"] == "OTHER").sum()
    total_non_empty = (df["status"] != "NO_DATA").sum()
    if total_non_empty > 0:
        other_pct = other_total / total_non_empty * 100
        if other_pct > 5:
            warnings.append(
                f"ℹ {other_total} cells ({other_pct:.1f}% of non-empty) are classified as OTHER — "
                "these don't match known patterns (LP*, MT*, RM, LRM, DH, DP, ACC, TNST, ULP) "
                "and aren't highlighted as routes."
            )

    # Manual vs computed trip count — compare per contractor since only some have manual counts
    for contractor in df["contractor"].unique():
        sub = df[df["contractor"] == contractor]
        manual_total = sub[sub["manual_trip_count"].notna()].groupby("vehicle")["manual_trip_count"].max().sum()
        if manual_total == 0:
            continue
        # Only count highlighted cells for vehicles that have manual counts
        vehicles_with_manual = sub[sub["manual_trip_count"].notna()]["vehicle"].unique()
        computed_for_those = int(sub[sub["vehicle"].isin(vehicles_with_manual)]["is_highlighted"].sum())
        diff = computed_for_those - int(manual_total)
        pct = abs(diff) / manual_total * 100 if manual_total else 0
        if pct > 15:
            warnings.append(
                f"⚠ {contractor}: computed trips ({computed_for_those}) differ from "
                f"Excel Trip column ({int(manual_total)}) by {diff:+d} ({pct:.1f}%). "
                "Verify the highlighting in the Excel file."
            )

    return warnings
