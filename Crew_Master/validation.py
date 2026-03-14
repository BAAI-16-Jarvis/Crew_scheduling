import pandas as pd
def prepare_crew_data(df):

    # Reads the Crew sheet and prepares:
    # 1) crew_quals → {crew_name: [qualified aircraft models]}
    # 2) crew_roles → {crew_name: role (PIC/SIC/FO)}
    # 3) cleaned crew dataframe

    # This data is later used by the optimizer to:
    #  • check aircraft qualification
    #  • enforce PIC/SIC roles
    #  • create decision variables only for valid crew


    #df = pd.read_excel(crew_path, sheet_name='Crew', header=1)

    # Forward fill person-specific info as it's merged across qualification rows
    cols_to_ffill = ['Name', 'Employee No', 'Nationality', 'Base city', 'Designation', 'On duty as']
    df[cols_to_ffill] = df[cols_to_ffill].ffill()
    # Remove empty rows
    df = df.dropna(subset=['Name'])

    # df = df[~df['Applicable models'].str.contains('Simulator')]

    # Create a mapping of Crew to their qualified Models, filtering out 'Simulator'
    crew_quals = df.groupby('Name')['Applicable models'].apply(list).to_dict()

    # Create a mapping of Crew to their Role (PIC vs SIC)
    crew_roles = df.drop_duplicates('Name').set_index('Name')['On duty as'].to_dict()

    print(crew_quals);

    return crew_quals, crew_roles, df

def prepare_sector_data(df):
    """
    Prepares sector data for FAA-compliant crew scheduling.
    Computes all time-based metrics required by the CP-SAT model.
    """

    # -----------------------------
    # AIRCRAFT PARSING
    # -----------------------------
    # Example: N881YV(BOEING/767-200SF)
    # Corrected regex to ensure two capturing groups are extracted
    df[['Reg', 'Model']] = df['Aircraft'].str.extract(r'([^\(]+)\((.+)\)')

    # Clean time columns by removing '0 days ' prefix
    time_cols = ['UTC Flight Start Time', 'UTC Flight End Time', 'UTC Flight Duty Start Time', 'UTC Flight Duty End Time']
    for col in time_cols:
       df[col] = df[col].astype(str).str.replace('0 days ', '', regex=False)

    # Convert times to datetime objects, explicitly converting 'Date' to string first
    df['StartDT'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['UTC Flight Start Time'].astype(str))
    df['EndDT'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['UTC Flight End Time'].astype(str))

    # Handle overnight flights (End time < Start time) and increment EndDT by 1
    # mask is the list of all Rows where EndDT < StartDT (Midnight activity)
    # loc[mask, EndDT] gives the cells where the Update has to be done in place

    mask = df['EndDT'] < df['StartDT']
    print('\nBefore Increment\n')
    print((df.loc[mask,'EndDT']))

    df.loc[mask, 'EndDT'] += pd.Timedelta(days=1)

    print('\nAfter Increment\n')
    print((df.loc[mask,'EndDT']))

    # Same for Duty Times
    df['DutyStartDT'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['UTC Flight Duty Start Time'].astype(str))
    df['DutyEndDT'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['UTC Flight Duty End Time'].astype(str))
    mask_duty = df['DutyEndDT'] < df['DutyStartDT']
    df.loc[mask_duty, 'DutyEndDT'] += pd.Timedelta(days=1)

    # -----------------------------
    # FAA TIME METRICS (VECTORISED)
    # -----------------------------
    df['FTL_hours'] = (
        (df['EndDT'] - df['StartDT'])
        .dt.total_seconds() / 3600
    )

    df['FDTL_hours'] = (
        (df['DutyEndDT'] - df['DutyStartDT'])
        .dt.total_seconds() / 3600
    )

    # -----------------------------
    # FAA GROUPING KEYS
    # -----------------------------
    df['duty_date'] = df['DutyStartDT'].dt.date

    # Week start (FAA weekly rest logic)
    df['week'] = (
        df['DutyStartDT']
        .dt.to_period('W')
        .apply(lambda r: r.start_time)
    )

    # Month & Year (FTL accumulation)
    df['month'] = df['DutyStartDT'].dt.to_period('M')
    df['year'] = df['DutyStartDT'].dt.year

    # -----------------------------
    # SORT ON DUTY START (IMPORTANT)
    # -----------------------------
    df = df.sort_values('DutyStartDT').reset_index(drop=True)

    print(df.head())
    return df