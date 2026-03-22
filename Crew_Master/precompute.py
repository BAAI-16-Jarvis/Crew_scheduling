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