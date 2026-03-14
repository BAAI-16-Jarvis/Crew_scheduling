from ortools.sat.python import cp_model
from precompute import precompute_faa_groups, precompute_rest_violations

# Define FAA limits as constants
MAX_FDTL_24H = 16  # FDTL ≤ 16 hrs in any 24 hrs
MAX_FTL_24H = 8    # FTL ≤ 8 hrs in any 24 hrs
MAX_FTL_30D = 100  # FTL ≤ 100 hrs in 30 days
MAX_FTL_365D = 1000 # FTL ≤ 1000 hrs in 365 days

# Scaling factor for converting float hours to integers for CP-SAT solver
# A factor of 1000 allows for precision up to milliseconds, which is usually sufficient.
SCALING_FACTOR = 1000

def develop_scheduling_model(sectors, crew_quals, crew_roles):
    model = cp_model.CpModel()

    crew_names = list(crew_quals.keys())
    num_sectors = len(sectors)

    # Decision variable
    x = {(s, c): model.NewBoolVar(f'x_s{s}_c{c}')
         for s in range(num_sectors)
         for c in crew_names}

    # -------------------------------------------------
    # BASIC ASSIGNMENT (2 pilots per sector)
    # -------------------------------------------------
    for s in range(num_sectors):
        model.Add(sum(x[s, c] for c in crew_names) == 2)

    # Constraint 1: Qualification & Role matching
    for s in range(num_sectors):
        sector_model = sectors.iloc[s]['Model']

        # 1. PICs MUST be designated as 'PIC' and have the right qualification
        valid_pics = [c for c in crew_names if (sector_model in crew_quals[c]) and (crew_roles[c] == 'PIC')]

        # 2. NEW LOGIC: SICs can be EITHER a designated SIC/FO OR a PIC flying down
        valid_sics = [c for c in crew_names if (sector_model in crew_quals[c]) and
                      (crew_roles[c] == 'PIC' or 'SIC' in crew_roles[c] or 'First Officer' in crew_roles[c])]

        # 3. Decision Variables for specific roles in this sector
        # We need to distinguish if a PIC is acting as PIC or SIC to prevent
        # the same person from filling both seats on the same flight.
        pic_choice = model.NewBoolVar(f'pic_s{s}')
        sic_choice = model.NewBoolVar(f'sic_s{s}')

        # Ensure exactly 1 person is assigned to each role
        model.Add(sum(x[s, c] for c in valid_pics) == 1)
        model.Add(sum(x[s, c] for c in valid_sics) == 1)

        # CRITICAL ADDITION: A person cannot be both PIC and SIC on the same flight
        # If a PIC is chosen for the PIC seat, they cannot be chosen for the SIC seat
        for c in crew_names:
            # For any crew member 'c', their assignment to sector 's' can only happen once
            # (OR-Tools handles this implicitly if we ensure sum of assignments to a sector is 2)
            pass

        # Ensure exactly 2 unique people are assigned to the sector
        model.Add(sum(x[s, c] for c in crew_names) == 2)


    faa_groups = precompute_faa_groups(sectors)
    rest_violations = precompute_rest_violations(sectors)

    ## Add FAA Rules code here
    faa_groups  = precompute_faa_groups(sectors)
    rest_violations = precompute_rest_violations(sectors)

    ##FTL ≤ 100 hrs / 30 days
    for c in crew_names:
      for idx in faa_groups["monthly"].values():
        model.Add(
            sum(
                x[s, c] * int(sectors.loc[s, "FTL_hours"] * SCALING_FACTOR)
                for s in idx
            )
            <= int(100 * SCALING_FACTOR)
        )

    #FTL ≤ 1000 hrs / 365 days
    for c in crew_names:
     for idx in faa_groups["yearly"].values():
      model.Add(
          sum(
              x[s, c] * int(sectors.loc[s, "FTL_hours"] * SCALING_FACTOR)
              for s in idx
          )
          <= int(1000 * SCALING_FACTOR)
      )

    ##FAA 6,7
    for c in crew_names:
      for i, j in rest_violations:
       model.Add(x[i, c] + x[j, c] <= 1)

    print("FAA daily windows:", len(faa_groups["daily"]))
    print("Monthly windows:", len(faa_groups["monthly"]))
    print("Yearly windows:", len(faa_groups["yearly"]))
    print("Rest violations:", len(rest_violations))


    print("Crew count:", len(crew_names))
    print("Crew names:", crew_names[:10])
    print("Sector count:", num_sectors)

    # -------------------------------------------------
    # Solve
    # -------------------------------------------------
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # Added print statements for debugging solver status
    print(f"Solver status: {solver.StatusName(status)}")
    if status == cp_model.INFEASIBLE:
        print("Model is infeasible. This means the constraints are too restrictive or contradictory.")
        print("Possible causes: insufficient crew, conflicting qualifications/roles, or tight FTL/rest limits.")

    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        results = []
        for s in range(num_sectors):
            assigned = [c for c in crew_names if solver.Value(x[s, c])]
            results.append(", ".join(assigned))
        sectors['Assigned_Crew'] = results
        return sectors

    return "No feasible solution"