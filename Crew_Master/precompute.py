def precompute_faa_groups(sectors):
    groups = {}

    groups['daily'] = sectors.groupby('duty_date').apply(lambda x: x.index.tolist()).to_dict()
    groups['weekly'] = sectors.groupby('week').apply(lambda x: x.index.tolist()).to_dict()
    groups['monthly'] = sectors.groupby('month').apply(lambda x: x.index.tolist()).to_dict()
    groups['yearly'] = sectors.groupby('year').apply(lambda x: x.index.tolist()).to_dict()

    return groups



def precompute_rest_violations(sectors):
    violations = []

    sorted_df = sectors.sort_values('DutyStartDT')
    idxs = sorted_df.index.tolist()

    for i, j in zip(idxs[:-1], idxs[1:]):
        rest_gap = (
            sectors.loc[j, 'DutyStartDT'] -
            sectors.loc[i, 'DutyEndDT']
        ).total_seconds() / 3600

        prev_ftl = sectors.loc[i, 'FTL_hours']

        if prev_ftl <= 8 and rest_gap < 8:
            violations.append((i, j))
        elif prev_ftl > 8 and rest_gap < 16:
            violations.append((i, j))

    return violations

