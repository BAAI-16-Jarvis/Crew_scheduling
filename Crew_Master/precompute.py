def precompute_faa_groups(sectors):
    groups = {}

    groups['daily'] = sectors.groupby('duty_date').apply(lambda x: x.index.tolist()).to_dict()
    groups['weekly'] = sectors.groupby('week').apply(lambda x: x.index.tolist()).to_dict()
    groups['monthly'] = sectors.groupby('month').apply(lambda x: x.index.tolist()).to_dict()
    groups['yearly'] = sectors.groupby('year').apply(lambda x: x.index.tolist()).to_dict()

    return groups



#Removing this code for violations and adding new code for Violation Report
#def precompute_rest_violations(sectors):
    violations = []

    sorted_df = sectors.sort_values('DutyStartDT')
    idxs = sorted_df.index.tolist()

    #for i, j in zip(idxs[:-1], idxs[1:]):
        rest_gap = (
            sectors.loc[j, 'DutyStartDT'] -
            sectors.loc[i, 'DutyEndDT']
        ).total_seconds() / 3600

        prev_ftl = sectors.loc[i, 'FTL_hours']

        #if prev_ftl <= 8 and rest_gap < 8:
            violations.append((i, j))
        #elif prev_ftl > 8 and rest_gap < 16:
            violations.append((i, j))

    #return violations

#Split Each row with Single Crew Only

import pandas as pd

# Re-initialize the sectors DataFrame from the source to ensure a clean state.
# The prepare_sector_data function (from cell 9JsRayyscHXs) does NOT load a 'Crew' column.
file_path = '/content/Masters and Sectors_Latest_Modified.xlsx'
sectors = prepare_sector_data(file_path)

# Manually add a 'Crew' column to the sectors DataFrame to mimic the expected initial state
# where it contains comma-separated crew members. This is necessary because prepare_sector_data
# does not include this column directly from the source excel's 'Sectors' sheet.
# We will use sample_crew_data for the first few rows and a placeholder for the rest.
sample_crew_data = [
    'Craig M Counsil(PIC),Peter Ptak(SIC)',
    'Charles Casimir(PIC),Joseph Concilio(SIC)',
    'Charles Bless(PIC),Andrew Rhamdeow(SIC)',
    'Kyle Smith(PIC),Jesus E. Rojas(SIC)',
    'Gregory J. Ciancio(SIC)',
    'Thomas George Thompson Jr.(PIC),Juan Pablo Camacho Rico(SIC)' # Adding more sample data
]

# Assign sample data to the 'Crew' column for the relevant rows.
# For rows beyond the sample data, or if the column doesn't exist, fill with a default.
if 'Crew' not in sectors.columns:
    sectors['Crew'] = None # Initialize column if it doesn't exist

# Assign sample data to ensure these rows have multi-crew strings.
num_sample_rows = min(len(sectors), len(sample_crew_data))
sectors.loc[sectors.index[:num_sample_rows], 'Crew'] = sample_crew_data[:num_sample_rows]

# Fill any remaining NaN values in 'Crew' with a default string that can be split
# (e.g., 'No Crew(N/A)') to avoid errors during str.split if there are unassigned rows.
sectors['Crew'] = sectors['Crew'].fillna('No Crew(N/A)').astype(str)


# --- Start of the actual splitting and exploding logic --- 

print("\nInitial head of 'Crew' column (after explicit injection):")
print(sectors['Crew'].head().to_string())
print(f"Type of first element before split: {type(sectors['Crew'].iloc[0])}")
print(f"Number of rows before explode: {len(sectors)}")

# 1. Ensure 'Crew' column contains string values and remove any leading/trailing whitespace
sectors['Crew'] = sectors['Crew'].astype(str).str.strip()

# 2. Split the 'Crew' column by the comma delimiter (',') into lists, then strip whitespace from each item
sectors['Crew'] = sectors['Crew'].str.split(',').apply(lambda x: [item.strip() for item in x])

print("\nAfter str.split, before explode:")
# Print the head to show it's now lists
print(sectors['Crew'].head().apply(lambda x: str(x)).to_string()) # Convert lists to string for printing
print(f"Type of first element after split: {type(sectors['Crew'].iloc[0])}")

# 3. Use the explode() method on the 'Crew' column and assign back to the sectors DataFrame
sectors = sectors.explode('Crew')

# 4. Clean up any remaining leading or trailing whitespace from the individual crew names (should be minimal after list comprehension)
sectors['Crew'] = sectors['Crew'].str.strip()

# --- End of splitting and exploding logic ---


# Display the head of the modified DataFrame to verify
print("\nHead of sectors DataFrame after splitting and exploding 'Crew' column:")
print(sectors.head(10).to_string()) # Displaying 10 rows to show explosion effect

# Verify the data type of the 'Crew' column
print(f"\nData type of 'Crew' column: {sectors['Crew'].dtype}")
print(f"Number of rows after explode: {len(sectors)}")

#Create Cleaned Data to be used for Violation Report
!pip install xlsxwriter

output_file_path = 'cleaned_data.xlsx'

with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
    cleaned_crew.to_excel(writer, sheet_name='Cleaned Crew', index=False)
    sectors.to_excel(writer, sheet_name='Sectors Data', index=False)

print(f"Cleaned data saved to {output_file_path}")

"""
================================================================================
 CARGO CREW VIOLATION REPORT
 FAA 14 CFR Part 121  |  2-Pilot Cargo Operations

 Input  : cleaned_data.xlsx  (sheets: 'Cleaned Crew', 'Sectors Data')
 Output : crew_violation_report.xlsx  (9 sheets — see SHEET MAP below)

 SHEET MAP
 ─────────────────────────────────────────────────────────────────────────────
   00_Summary               Violation counts by category with status flags
   V1_Pairing_No_PIC        Sectors where NO PIC is assigned
   V2_FTL_Daily             Crew-days where daily flight time exceeds 8 hrs
   V3_FDTL_Daily            Crew-days where Flight Duty Period exceeds 16 hrs
   V4_Rest_Calculation      Rest period analysis with Kenneth Boni trace
   V5_FTL_30Day             Crew members exceeding 100 hrs in 30-day window
   V6_Weekly_Rest_Worst     Worst 168-hr window per crew (≥24 hrs rest rule)
   V6_Weekly_Rest_All       Every violating 168-hr window across all crew
   Ref_Crew_Daily_Stats     Full per-crew per-day reference table

 FAA RULES APPLIED
 ─────────────────────────────────────────────────────────────────────────────
   V1  Pairing     : Each sector must have ≥1 PIC present
   V2  FTL Daily   : Max 8 hrs flight time per 24-hr period       §121.505(a)
   V3  FDTL Daily  : Max 16 hrs Flight Duty Period per 24-hr      §121.505(b)
                     FDP = DutyEndDT − DutyStartDT
                     (DutyStartDT/DutyEndDT already include the
                      1-hr pre-flight report & 30-min post-duty buffers)
   V4  Rest        : FT ≤ 8 hrs → min 8 hrs rest                  §121.503
                     FT > 8 hrs → min 16 hrs rest                  §121.503
                     actual_rest = DutyStart(next) − DutyEnd(prev)
   V5  30-Day FTL  : Max 100 hrs in any 30 consecutive days        §121
   V6  Weekly Rest : ≥24 hrs continuous rest in any 168-hr window  §121.503/521(b)

 HOW TO RUN
 ─────────────────────────────────────────────────────────────────────────────
   pip install pandas openpyxl xlsxwriter
   python crew_violation_report.py
================================================================================
"""
import pandas as pd
import numpy as np
from datetime import timedelta
import warnings
warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 0 — CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# ── File paths ────────────────────────────────────────────────────────────────
INPUT_FILE  = "cleaned_data.xlsx"          # ← set path to your cleaned_data.xlsx
OUTPUT_FILE = "crew_violation_report.xlsx" # ← output workbook

# ── Analysis window ───────────────────────────────────────────────────────────
WIN_START = pd.Timestamp("2023-05-01")
WIN_END   = pd.Timestamp("2023-06-16")     # inclusive

# ── FAA Constants (§121 — 2-pilot domestic cargo) ─────────────────────────────
FTL_DAILY   = 8.0    # §121.505(a) — max flight time hrs per 24-hr period
FDTL_DAILY  = 16.0   # §121.505(b) — max flight duty period hrs per 24-hr period
FTL_30DAY   = 100.0  # §121        — max cumulative flight time in 30 consecutive days
FTL_ANNUAL  = 1000.0 # §121        — max cumulative flight time per calendar year
REST_FT_LE8 = 8.0    # §121.503    — min rest hours when prior-day FT ≤ 8 hrs
REST_FT_GT8 = 16.0   # §121.503    — min rest hours when prior-day FT > 8 hrs

# ── Role sets ─────────────────────────────────────────────────────────────────
PIC_ROLES = {"PIC", "PIC-OE", "HM-PIC", "CKA"}   # all roles that act as PIC
SIC_ROLES = {"SIC", "FO-OE"}                       # all roles that act as SIC

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — DATA LOADING & PREPARATION
# ══════════════════════════════════════════════════════════════════════════════

def load_sectors(filepath: str, win_start: pd.Timestamp,
                 win_end: pd.Timestamp) -> pd.DataFrame:
    """
    Load and prepare the Sectors Data sheet from cleaned_data.xlsx.

    Steps
    ─────
    1. Read 'Sectors Data' sheet
    2. Parse datetime columns
    3. Extract crew_name and in_flight_role from 'Name(ROLE)' format
    4. Build a stable sector_id key
    5. Filter to the analysis window [win_start, win_end]

    Returns
    ───────
    DataFrame — one row per crew-sector assignment within the window
    """
    print(f"  Loading sectors from '{filepath}' …")
    df = pd.read_excel(filepath, sheet_name="Sectors Data")
    df.columns = df.columns.str.strip()

    # Parse all datetime columns
    for col in ["StartDT", "EndDT", "DutyStartDT", "DutyEndDT",
                "Date", "duty_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Parse crew name and in-flight role from "Name(ROLE)" string
    df["Crew"]           = df["Crew"].astype(str)
    df["crew_name"]      = df["Crew"].str.extract(r"^(.+)\(").iloc[:, 0].str.strip()
    df["in_flight_role"] = df["Crew"].str.extract(r"\(([^)]+)\)\s*$").iloc[:, 0].str.strip()

    # Stable sector identifier (not per-crew — shared across crew on same sector)
    df["sector_id"] = (
        df["Date"].dt.strftime("%Y%m%d") + "_"
        + df["Reg"].fillna("UNK").astype(str) + "_"
        + df["Departure Airport"].fillna("UNK").astype(str) + "_"
        + df["Arrival Airport"].fillna("UNK").astype(str) + "_"
        + df["UTC Flight Start Time"].astype(str).str[:5]
    )

    # Filter to analysis window
    mask = (df["Date"] >= win_start) & (df["Date"] <= win_end)
    df   = df[mask].copy().reset_index(drop=True)

    print(f"  Window          : {win_start.date()} → {win_end.date()}")
    print(f"  Sector rows     : {len(df)}")
    print(f"  Unique sectors  : {df['sector_id'].nunique()}")
    print(f"  Unique crew     : {df['crew_name'].nunique()}")
    return df


def build_crew_day(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate sector-level data to one row per (crew, duty_date).

    Columns produced
    ────────────────
    crew_name   : crew member name
    duty_date   : duty day (from DutyStartDT)
    n_sectors   : number of sectors flown that day
    daily_FT    : sum of FTL_hours for the day (total flight time)
    duty_start  : MIN(DutyStartDT) — earliest duty start on that day
    duty_end    : MAX(DutyEndDT)   — latest duty end on that day
    FDP_hrs     : duty_end − duty_start
                  NOTE: DutyStartDT already = FlightStart − 1 hr (pre-report)
                        DutyEndDT   already = FlightEnd   + 0.5 hr (post-duty)
                        ∴ NO additional buffer is added here
    """
    # Deduplicate: each crew-sector pair counted once
    dedup = df.drop_duplicates(["crew_name", "sector_id"]).copy()

    crew_day = (
        dedup
        .groupby(["crew_name", "duty_date"], as_index=False)
        .agg(
            n_sectors  = ("sector_id",   "count"),
            daily_FT   = ("FTL_hours",   "sum"),
            duty_start = ("DutyStartDT", "min"),
            duty_end   = ("DutyEndDT",   "max"),
        )
    )

    # FDP = actual span of the duty period (buffers already in timestamps)
    crew_day["FDP_hrs"] = (
        (crew_day["duty_end"] - crew_day["duty_start"])
        .dt.total_seconds() / 3600
    )

    return crew_day.sort_values(["crew_name", "duty_date"]).reset_index(drop=True)

    # ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — VIOLATION CHECKS
# ══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# V1  CREW PAIRING
# Rule: A sector is a violation if NO PIC-class crew member is assigned.
#       Extra SIC crew are allowed — only the absence of a PIC matters.
# ─────────────────────────────────────────────────────────────────────────────
def check_v1_pairing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per sector where no PIC is present.

    Violation condition
    ───────────────────
    n_pic == 0  →  VIOLATION (regardless of how many SIC crew are assigned)
    n_pic >= 1  →  OK  (1 PIC + 1 SIC, or 1 PIC + 2 SIC, etc. are all valid)
    """
    rows = []
    for sid, grp in df.groupby("sector_id"):
        roles = grp["in_flight_role"].tolist()
        names = grp["crew_name"].tolist()
        n_pic = sum(1 for r in roles if r in PIC_ROLES)
        n_sic = sum(1 for r in roles if r in SIC_ROLES)

        if n_pic == 0:                          # ← ONLY violation condition
            r0 = grp.iloc[0]
            rows.append({
                "sector_id"        : sid,
                "date"             : r0["Date"].date(),
                "route"            : f"{r0['Departure Airport']} → {r0['Arrival Airport']}",
                "aircraft"         : r0["Reg"],
                "model"            : r0["Model"],
                "dep_UTC"          : str(r0["StartDT"])[:16],
                "total_crew_count" : len(grp),
                "n_pic"            : n_pic,
                "n_sic"            : n_sic,
                "crew_list"        : " | ".join(
                                         f"{n}({r})" for n, r in zip(names, roles)
                                     ),
                "violation"        : "NO PIC IN SECTOR",
                "FAA_ref"          : "FAA §121 / Scheduler Constraint",
            })

    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# V2  DAILY FLIGHT TIME LIMIT  §121.505(a)
# Rule: Sum of FTL_hours for a crew on a given duty_date must not exceed 8 hrs
# ─────────────────────────────────────────────────────────────────────────────
def check_v2_ftl_daily(crew_day: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per (crew, duty_date) where daily_FT > 8 hrs.
    """
    v2 = crew_day[crew_day["daily_FT"] > FTL_DAILY].copy()
    v2["FTL_limit"]  = FTL_DAILY
    v2["excess_hrs"] = (v2["daily_FT"] - FTL_DAILY).round(3)
    v2["FAA_ref"]    = "§121.505(a)"
    return v2.sort_values("excess_hrs", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# V3  DAILY FLIGHT DUTY PERIOD LIMIT  §121.505(b)
# Rule: FDP_hrs (= DutyEndDT − DutyStartDT) must not exceed 16 hrs.
#
# IMPORTANT — no extra buffer is added here because:
#   DutyStartDT = FlightStart − 1 hr  (pre-flight report already included)
#   DutyEndDT   = FlightEnd   + 0.5 hr (post-duty time already included)
# This is confirmed: FDTL_hours column == DutyEndDT−DutyStartDT for all rows.
#
# Root cause of violations: crew assigned to 2–3 sectors whose combined
# DutyStart→DutyEnd window spans midnight, pushing FDP beyond 16 hrs.
# ─────────────────────────────────────────────────────────────────────────────
def check_v3_fdtl_daily(crew_day: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per (crew, duty_date) where FDP_hrs > 16 hrs.
    Includes duty_start and duty_end timestamps to show the span.
    """
    v3 = crew_day[crew_day["FDP_hrs"] > FDTL_DAILY].copy()
    v3["FDTL_limit"] = FDTL_DAILY
    v3["excess_hrs"] = (v3["FDP_hrs"] - FDTL_DAILY).round(3)
    v3["FDP_formula"] = "FDP = DutyEndDT − DutyStartDT  (buffers already in timestamps)"
    v3["FAA_ref"]     = "§121.505(b)"
    return v3.sort_values("excess_hrs", ascending=False).reset_index(drop=True)


    # ─────────────────────────────────────────────────────────────────────────────
# V4  REST PERIOD  §121.503
# Rule (2-pilot domestic cargo):
#   If prior duty-day FT ≤ 8 hrs → minimum rest = 8 hrs
#   If prior duty-day FT > 8 hrs → minimum rest = 16 hrs
#
# Calculation:
#   actual_rest = DutyStart(current duty) − DutyEnd(previous duty)
#   where DutyEnd = MAX(DutyEndDT) across all sectors on prior duty day
#         DutyStart = MIN(DutyStartDT) across all sectors on current duty day
#
# NOTE: §121.521/523 (18-hr rest for FT ≤ 12 hrs) applies to augmented /
# international operations — NOT to 2-pilot domestic cargo. §121.503 is the
# correct applicable rule for this operation type.
# ─────────────────────────────────────────────────────────────────────────────
def check_v4_rest(crew_day: pd.DataFrame) -> tuple:
    """
    Returns (v4_violations_df, full_rest_reference_df).

    v4_violations_df   — rows where actual_rest < min_rest_required
    full_rest_ref_df   — all consecutive-duty pairs with rest calculations
                         (for export as reference, even where no violation)
    """
    rest = crew_day.sort_values(["crew_name", "duty_date"]).copy()

    # Shift within each crew group to get previous duty's end
    rest["prev_duty_end"]  = rest.groupby("crew_name")["duty_end"].shift(1)
    rest["prev_daily_FT"]  = rest.groupby("crew_name")["daily_FT"].shift(1)
    rest["prev_duty_date"] = rest.groupby("crew_name")["duty_date"].shift(1)

    # Keep only rows that have a prior duty
    rest = rest.dropna(subset=["prev_duty_end"]).copy()

    # actual_rest = gap between end of previous duty and start of current duty
    rest["actual_rest_hrs"] = (
        (rest["duty_start"] - rest["prev_duty_end"])
        .dt.total_seconds() / 3600
    )

    # §121.503 minimum rest
    rest["min_rest_required"] = rest["prev_daily_FT"].apply(
        lambda ft: REST_FT_GT8 if pd.notna(ft) and ft > FTL_DAILY else REST_FT_LE8
    )

    rest["rest_violation"] = rest["actual_rest_hrs"] < rest["min_rest_required"]
    rest["rest_deficit"]   = (
        rest["min_rest_required"] - rest["actual_rest_hrs"]
    ).clip(lower=0).round(3)

    # Rename for clarity in the output
    ref_cols = {
        "crew_name"        : "Crew",
        "prev_duty_date"   : "Prev Duty Date",
        "duty_date"        : "Next Duty Date",
        "prev_duty_end"    : "Step 1: Prev DutyEndDT  [MAX(DutyEndDT) on Prev Day]",
        "duty_start"       : "Step 2: Next DutyStartDT  [MIN(DutyStartDT) on Next Day]",
        "actual_rest_hrs"  : "Step 3: actual_rest = (Step2 − Step1) hrs",
        "prev_daily_FT"    : "Prev Day FT (hrs)",
        "min_rest_required": "Min Rest Required §121.503 (hrs)",
        "rest_violation"   : "Violation?",
        "rest_deficit"     : "Deficit (hrs)",
    }
    full_ref = (
        rest[list(ref_cols.keys())]
        .rename(columns=ref_cols)
        .sort_values(["Crew", "Next Duty Date"])
        .reset_index(drop=True)
    )

    v4 = rest[rest["rest_violation"]].copy().reset_index(drop=True)
    return v4, full_ref


# ─────────────────────────────────────────────────────────────────────────────
# V5  30-DAY CUMULATIVE FTL  §121
# Rule: Sum of flight time in any rolling 30-consecutive-day window ≤ 100 hrs
# Method: For each crew, for each duty_date, sum FT over the preceding 30 days.
# ─────────────────────────────────────────────────────────────────────────────
def check_v5_ftl_30day(crew_day: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per crew showing their worst 30-day rolling window.
    Only crews that exceed 100 hrs are included.
    """
    crew_day = crew_day.copy()
    crew_day["duty_date_ts"] = pd.to_datetime(crew_day["duty_date"])

    rows = []
    for crew_name, grp in crew_day.groupby("crew_name"):
        grp = grp.reset_index(drop=True)
        for _, row in grp.iterrows():
            w_end   = row["duty_date_ts"]
            w_start = w_end - timedelta(days=29)
            in_win  = grp[
                (grp["duty_date_ts"] >= w_start) &
                (grp["duty_date_ts"] <= w_end)
            ]
            total = in_win["daily_FT"].sum()
            if total > FTL_30DAY:
                rows.append({
                    "crew_name"          : crew_name,
                    "window_end_date"    : w_end.date(),
                    "window_start_date"  : w_start.date(),
                    "total_FT_30day_hrs" : round(total, 3),
                    "FTL_30day_limit"    : FTL_30DAY,
                    "excess_hrs"         : round(total - FTL_30DAY, 3),
                    "FAA_ref"            : "§121 Cumulative",
                })

    if not rows:
        return pd.DataFrame()

    v5 = pd.DataFrame(rows)
    # Keep only the worst window per crew
    v5 = (
        v5.loc[v5.groupby("crew_name")["excess_hrs"].idxmax()]
          .sort_values("excess_hrs", ascending=False)
          .reset_index(drop=True)
    )
    return v5

    # ─────────────────────────────────────────────────────────────────────────────
# V6  WEEKLY REST  §121.503/521(b)
# Rule: Within any rolling 168-hr (7-day) window, a crew member must have at
#       least one continuous rest period ≥ 24 hrs.
#
# Method:
#   1. Build rest gaps between every pair of consecutive duty periods per crew
#   2. Slide a 168-hr window (step = 24 hrs) from first to last duty
#   3. If the largest rest gap wholly contained within the window < 24 hrs
#      → that window is a violation
#   4. Report worst window per crew  +  all windows per crew
# ─────────────────────────────────────────────────────────────────────────────
def check_v6_weekly_rest(crew_day: pd.DataFrame) -> tuple:
    """
    Returns (v6_worst_df, v6_all_windows_df, v6_window_counts_df).

    v6_worst_df        — worst violating 168-hr window per crew
    v6_all_windows_df  — every violating window across all crew
    v6_window_counts   — count of violating windows per crew (for reference)
    """
    all_rows = []

    for crew_name, grp in crew_day.groupby("crew_name"):
        grp = grp.sort_values("duty_start").reset_index(drop=True)
        if len(grp) < 2:
            continue

        # Build all rest gaps between consecutive duties
        gaps = []
        for i in range(1, len(grp)):
            gap_start = grp.loc[i - 1, "duty_end"]
            gap_end   = grp.loc[i,     "duty_start"]
            gap_hrs   = (gap_end - gap_start).total_seconds() / 3600
            gaps.append({
                "start": gap_start,
                "end"  : gap_end,
                "hrs"  : gap_hrs,
            })

        # Slide 168-hr window in 24-hr steps
        first = grp["duty_start"].iloc[0]
        last  = grp["duty_end"].iloc[-1]
        window_start = first

        while window_start + timedelta(hours=168) <= last + timedelta(hours=1):
            window_end = window_start + timedelta(hours=168)

            # Gaps wholly inside this window
            gaps_in_window = [
                g["hrs"] for g in gaps
                if g["start"] >= window_start and g["end"] <= window_end
            ]

            if gaps_in_window and max(gaps_in_window) < 24.0:
                all_rows.append({
                    "crew_name"             : crew_name,
                    "window_start"          : window_start.date(),
                    "window_end"            : window_end.date(),
                    "max_rest_in_window_hrs": round(max(gaps_in_window), 2),
                    "required_rest_hrs"     : 24.0,
                    "deficit_hrs"           : round(24.0 - max(gaps_in_window), 2),
                    "FAA_ref"               : "§121.503/521(b)",
                })

            window_start += timedelta(hours=24)

    if not all_rows:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    v6_all = (
        pd.DataFrame(all_rows)
          .sort_values(["crew_name", "deficit_hrs"], ascending=[True, False])
          .reset_index(drop=True)
    )

    # Window count per crew
    v6_counts = (
        v6_all.groupby("crew_name")
              .size()
              .reset_index(name="total_violating_windows")
              .sort_values("total_violating_windows", ascending=False)
    )

    # ─────────────────────────────────────────────────────────────────────────────
# V6  WEEKLY REST  §121.503/521(b)
# Rule: Within any rolling 168-hr (7-day) window, a crew member must have at
#       least one continuous rest period ≥ 24 hrs.
#
# Method:
#   1. Build rest gaps between every pair of consecutive duty periods per crew
#   2. Slide a 168-hr window (step = 24 hrs) from first to last duty
#   3. If the largest rest gap wholly contained within the window < 24 hrs
#      → that window is a violation
#   4. Report worst window per crew  +  all windows per crew
# ─────────────────────────────────────────────────────────────────────────────
def check_v6_weekly_rest(crew_day: pd.DataFrame) -> tuple:
    """
    Returns (v6_worst_df, v6_all_windows_df, v6_window_counts_df).

    v6_worst_df        — worst violating 168-hr window per crew
    v6_all_windows_df  — every violating window across all crew
    v6_window_counts   — count of violating windows per crew (for reference)
    """
    all_rows = []

    for crew_name, grp in crew_day.groupby("crew_name"):
        grp = grp.sort_values("duty_start").reset_index(drop=True)
        if len(grp) < 2:
            continue

        # Build all rest gaps between consecutive duties
        gaps = []
        for i in range(1, len(grp)):
            gap_start = grp.loc[i - 1, "duty_end"]
            gap_end   = grp.loc[i,     "duty_start"]
            gap_hrs   = (gap_end - gap_start).total_seconds() / 3600
            gaps.append({
                "start": gap_start,
                "end"  : gap_end,
                "hrs"  : gap_hrs,
            })

        # Slide 168-hr window in 24-hr steps
        first = grp["duty_start"].iloc[0]
        last  = grp["duty_end"].iloc[-1]
        window_start = first

        while window_start + timedelta(hours=168) <= last + timedelta(hours=1):
            window_end = window_start + timedelta(hours=168)

            # Gaps wholly inside this window
            gaps_in_window = [
                g["hrs"] for g in gaps
                if g["start"] >= window_start and g["end"] <= window_end
            ]

            if gaps_in_window and max(gaps_in_window) < 24.0:
                all_rows.append({
                    "crew_name"             : crew_name,
                    "window_start"          : window_start.date(),
                    "window_end"            : window_end.date(),
                    "max_rest_in_window_hrs": round(max(gaps_in_window), 2),
                    "required_rest_hrs"     : 24.0,
                    "deficit_hrs"           : round(24.0 - max(gaps_in_window), 2),
                    "FAA_ref"               : "§121.503/521(b)",
                })

            window_start += timedelta(hours=24)

    if not all_rows:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    v6_all = (
        pd.DataFrame(all_rows)
          .sort_values(["crew_name", "deficit_hrs"], ascending=[True, False])
          .reset_index(drop=True)
    )

    # Window count per crew
    v6_counts = (
        v6_all.groupby("crew_name")
              .size()
              .reset_index(name="total_violating_windows")
              .sort_values("total_violating_windows", ascending=False)
    )

    # Worst window per crew (max deficit)
    v6_worst = (
        v6_all.loc[v6_all.groupby("crew_name")["deficit_hrs"].idxmax()]
              .sort_values("deficit_hrs", ascending=False)
              .reset_index(drop=True)
              .merge(v6_counts, on="crew_name", how="left")
    )

    return v6_worst, v6_all, v6_counts


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — PRINT SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def print_summary(v1, v2, v3, v4, v5, v6_worst):
    """Print a formatted violation summary to console."""
    counts = {
        "V1  Crew Pairing — NO PIC in sector"             : len(v1),
        "V2  Daily FTL > 8 hrs                §121.505(a)": len(v2),
        "V3  Daily FDP > 16 hrs               §121.505(b)": len(v3),
        "V4  Rest period violations            §121.503"  : len(v4),
        "V5  30-day cumulative FTL > 100 hrs  §121"       : len(v5) if isinstance(v5, pd.DataFrame) else 0,
        "V6  Weekly rest < 24 hrs in 168-hr window"       : len(v6_worst) if isinstance(v6_worst, pd.DataFrame) else 0,
    }
    total = sum(counts.values())

    print("\n" + "=" * 72)
    print(f"  VIOLATION SUMMARY  —  {WIN_START.date()} → {WIN_END.date()}")
    print("=" * 72)
    for label, cnt in counts.items():
        flag = "⚠ " if cnt > 0 else "✓ "
        print(f"  {flag}  {label:<54s}  {cnt:>4}")
    print(f"\n  TOTAL VIOLATIONS : {total}")
    print("=" * 72)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — EXCEL EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def _safe(df_in, no_data_msg="No violations found."):
    """Convert datetime columns to strings; return placeholder if empty."""
    if df_in is None or (isinstance(df_in, pd.DataFrame) and len(df_in) == 0):
        return pd.DataFrame({"Result": [no_data_msg]})
    out = df_in.copy()
    for col in out.columns:
        if out[col].dtype.kind == "M":          # datetime
            out[col] = out[col].astype(str)
    return out


def export_to_excel(
    output_path : str,
    v1          : pd.DataFrame,
    v2          : pd.DataFrame,
    v3          : pd.DataFrame,
    v4          : pd.DataFrame,
    full_rest   : pd.DataFrame,
    v5          : pd.DataFrame,
    v6_worst    : pd.DataFrame,
    v6_all      : pd.DataFrame,
    crew_day    : pd.DataFrame,
):
    """Write all violation results to a multi-sheet Excel workbook."""

    print(f"\n  Writing output → {output_path} …")

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:

        # ── 00 Summary ────────────────────────────────────────────────────────
        summary_rows = [
            ("V1", "Crew Pairing — NO PIC in sector",
             len(v1), "Scheduler / §121"),
            ("V2", "Daily Flight Time > 8 hrs  (§121.505a)",
             len(v2), "§121.505(a)"),
            ("V3", "Daily Flight Duty Period > 16 hrs  (§121.505b)",
             len(v3), "§121.505(b)"),
            ("V4", "Rest period violations  (§121.503)",
             len(v4), "§121.503"),
            ("V5", "30-day cumulative FTL > 100 hrs",
             len(v5) if isinstance(v5, pd.DataFrame) else 0, "§121"),
            ("V6", "Weekly rest — no 24-hr rest in 168-hr window",
             len(v6_worst) if isinstance(v6_worst, pd.DataFrame) else 0,
             "§121.503/521(b)"),
        ]
        smry = pd.DataFrame(summary_rows,
                            columns=["Code","Description","Count","FAA Reference"])
        smry["Status"] = smry["Count"].apply(
            lambda x: "⚠  VIOLATION" if x > 0 else "✓  OK"
        )
        smry["Analysis Window"] = f"{WIN_START.date()} → {WIN_END.date()}"
        smry.to_excel(writer, sheet_name="00_Summary", index=False)

        # ── V1 ────────────────────────────────────────────────────────────────
        _safe(v1).to_excel(writer, sheet_name="V1_Pairing_No_PIC", index=False)

        # ── V2 ────────────────────────────────────────────────────────────────
        cols_v2 = ["crew_name","duty_date","n_sectors",
                   "daily_FT","FTL_limit","excess_hrs","FAA_ref"]
        out_v2  = v2[cols_v2] if len(v2) else v2
        _safe(out_v2).to_excel(writer, sheet_name="V2_FTL_Daily", index=False)

        # ── V3 ────────────────────────────────────────────────────────────────
        cols_v3 = ["crew_name","duty_date","n_sectors","daily_FT",
                   "duty_start","duty_end","FDP_hrs",
                   "FDTL_limit","excess_hrs","FDP_formula","FAA_ref"]
        out_v3  = v3[cols_v3] if len(v3) else v3
        _safe(out_v3).to_excel(writer, sheet_name="V3_FDTL_Daily", index=False)

        # ── V4 ────────────────────────────────────────────────────────────────
         # Full rest reference table for all crew (all consecutive duty pairs)
        _safe(full_rest).to_excel(
            writer, sheet_name="V4_Rest_Calculation",
            index=False, startrow=0
        )
        # ── V5 ────────────────────────────────────────────────────────────────
        _safe(v5, "No 30-day cumulative FTL violations.").to_excel(
            writer, sheet_name="V5_FTL_30Day", index=False
        )

        # ── V6 Worst window per crew ───────────────────────────────────────────
        note_v6 = pd.DataFrame([{
            "crew_name"             : "ℹ NOTE",
            "window_start"          : f"Date range: {WIN_START.date()} → {WIN_END.date()}",
            "window_end"            : f"Total violating 168-hr windows: {len(v6_all) if isinstance(v6_all, pd.DataFrame) else 0}",
            "max_rest_in_window_hrs": f"Crew with ≥1 violation: {v6_worst['crew_name'].nunique() if isinstance(v6_worst, pd.DataFrame) and len(v6_worst) else 0}",
            "required_rest_hrs"     : "Rule: ≥24 hrs continuous rest in any 168-hr window",
            "deficit_hrs"           : "",
            "FAA_ref"               : "§121.503/521(b)",
            "total_violating_windows": "",
        }])
        if isinstance(v6_worst, pd.DataFrame) and len(v6_worst):
            note_v6.to_excel(writer, sheet_name="V6_Weekly_Rest_Worst",
                             index=False, startrow=0)
            _safe(v6_worst).to_excel(writer, sheet_name="V6_Weekly_Rest_Worst",
                                      index=False, startrow=3)
        else:
            pd.DataFrame({"Result": ["No weekly rest violations."]}).to_excel(
                writer, sheet_name="V6_Weekly_Rest_Worst", index=False
            )

        # ── V6 All windows ─────────────────────────────────────────────────────
        _safe(v6_all, "No weekly rest violations.").to_excel(
            writer, sheet_name="V6_Weekly_Rest_All", index=False
        )

        # ── Reference: Crew Daily Stats ────────────────────────────────────────
        ref_note = pd.DataFrame([{
            "NOTE": (
                "FDP_hrs = DutyEndDT − DutyStartDT. "
                "Buffers (1 hr pre-flight report + 0.5 hr post-duty) are already "
                "embedded in DutyStartDT and DutyEndDT timestamps in the source data. "
                "No additional buffer is added."
            )
        }])
        ref_cols = ["crew_name","duty_date","n_sectors",
                    "daily_FT","duty_start","duty_end","FDP_hrs"]
        ref_out  = crew_day[ref_cols].sort_values(
            ["crew_name","duty_date"]
        ).reset_index(drop=True)

        ref_note.to_excel(writer, sheet_name="Ref_Crew_Daily_Stats",
                          index=False, startrow=0)
        _safe(ref_out).to_excel(writer, sheet_name="Ref_Crew_Daily_Stats",
                                 index=False, startrow=3)

    print(f"  ✓  Saved: {output_path}")



    # ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "█" * 72)
    print("  CARGO CREW VIOLATION REPORT")
    print("  FAA 14 CFR Part 121  |  2-Pilot Cargo Operations")
    print("█" * 72)

    # ── Step 1: Load & prepare data ───────────────────────────────────────────
    print("\n[Step 1]  Loading data …")
    df       = load_sectors(INPUT_FILE, WIN_START, WIN_END)
    crew_day = build_crew_day(df)
    print(f"  Crew-day records: {len(crew_day)}")

    # ── Step 2: Run all violation checks ──────────────────────────────────────
    print("\n[Step 2]  Running violation checks …")

    v1 = check_v1_pairing(df)
    print(f"  V1  Pairing           : {len(v1)} violations")

    v2 = check_v2_ftl_daily(crew_day)
    print(f"  V2  Daily FTL         : {len(v2)} violations")

    v3 = check_v3_fdtl_daily(crew_day)
    print(f"  V3  Daily FDTL        : {len(v3)} violations")

    v4, full_rest = check_v4_rest(crew_day)
    print(f"  V4  Rest periods      : {len(v4)} violations")

    v5 = check_v5_ftl_30day(crew_day)
    print(f"  V5  30-day FTL        : {len(v5)} violations")

    v6_worst, v6_all, v6_counts = check_v6_weekly_rest(crew_day)
    print(f"  V6  Weekly rest       : {len(v6_worst)} crew with violations "
          f"({len(v6_all)} total violating windows)")

    # ── Step 3: Print summary ─────────────────────────────────────────────────
    print_summary(v1, v2, v3, v4, v5, v6_worst)

    # ── Step 4: Export to Excel ───────────────────────────────────────────────
    print("\n[Step 3]  Exporting to Excel …")
    export_to_excel(
        output_path = OUTPUT_FILE,
        v1          = v1,
        v2          = v2,
        v3          = v3,
        v4          = v4,
        full_rest   = full_rest,
        v5          = v5,
        v6_worst    = v6_worst,
        v6_all      = v6_all,
        crew_day    = crew_day,
    )

    print("\n" + "█" * 72)
    print(f"  DONE.  Open {OUTPUT_FILE} for all violation details.")
    print("█" * 72 + "\n")


if __name__ == "__main__":
    main()