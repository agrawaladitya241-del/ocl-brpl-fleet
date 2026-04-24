# OCL / BRPL Fleet Intelligence Dashboard

Dashboard for tracking tipper trailer operations across OCL and BRPL contractors.

## What it does

Upload the monthly OCL/BRPL Excel report and get:

- **Overview** — KPIs + daily status trend chart
- **Vehicles** — Per-vehicle performance with manual vs computed trip counts, top performers, flagged vehicles, and drill-down showing exact DH/DP days
- **Groups** — Aggregated metrics per GROUP (BRPL, CNG, KOIRA, OCL, etc.)
- **Routes** — Unique route codes (D-SMC, OCL-DCL, B-M, etc.) with trip counts and per-vehicle breakdown
- **Accident Vehicles** — Grounded vehicles with date ranges
- **Audit / Verify** — Search + per-status cell listing to cross-check against Excel
- **Raw Data** — Full daily log, downloadable as CSV

## Status taxonomy

Each daily cell is classified (precedence top-down):

| Code | Meaning |
|---|---|
| ACCIDENT | ACC code or accident-related text |
| DH | Driver Home |
| DP | Driver Problem |
| LRM | Loading Raw Material |
| LP* | Loading Point at location X (LPD, LPB, LPOCL, etc.) |
| MT* | Empty Truck Movement (MTOCL, MT OCL, MTB, etc.) |
| RM | Raw Material loaded |
| TNST | In Transit |
| ULP | Unloading Point |
| TRIP | Highlighted cell (route marker) or ORIGIN-DESTINATION pattern |
| OTHER | Unknown code (flagged for review in Audit tab) |

## Trip counting

Trips are counted by highlighted cells in the Excel sheet — every blue-highlighted cell = one trip. This matches the BRPL manual Trip column with ~97% accuracy.

## Expected Excel format

- **OCL sheet** with columns: V NO, GROUP, MOB NO, days 1–22, LOCATION
- **BRPL sheet** with columns: Vehc No, GROUP, days 1–24, trip count (may have blank header)
- Other sheets (Sheet1, BRPL GPS, RAIGARH, Brpl) are ignored.

## Local setup

pip install -r requirements.txt
streamlit run app.py

## Deploy to Streamlit Community Cloud (free, no login)

1. Push this repo to a GitHub public repository.
2. Go to share.streamlit.io, sign in with GitHub.
3. Click "New app" → pick your repo → app.py as entry point → Deploy.
4. Get a public URL anyone can use.

## Project structure

- app.py — Streamlit UI (7 tabs)
- data_loader.py — Reads OCL + BRPL sheets, parses cells + highlighting
- analytics.py — Classification and summary builders
- requirements.txt
- README.md
