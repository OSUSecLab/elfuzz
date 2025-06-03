import sys
import os
import os.path
import pandas as pd

reps_dir = sys.argv[1]
cov_dir = sys.argv[2]

FUZZERS = [
    'elm',
    'alt',
    'grmr',
    'isla',
    'islearn'
]

POINTS = [600, 1200, 1800, 2400, 3000, 3600]

correct_dfs = []
for i in range(1, 6):
    dfs = {}
    for fuzzer in FUZZERS:
        df = pd.read_excel(
            os.path.join(reps_dir, f'rep{i}.xlsx'),
            sheet_name=fuzzer,
            header=0,
            index_col=0
        )
        covs = []
        cov_file = os.path.join(cov_dir, f'out{i}', f'libxml2_{fuzzer}', 'default', 'plot_data')
        with open(cov_file) as cov_f:
            last_time = 0
            first_line = True
            for l in cov_f:
                if first_line:
                    first_line = False
                    continue
                tokens = l.split(',')
                time = int(tokens[0].strip())
                count = int(tokens[-1].strip())
                for point in POINTS:
                    if time >= point and last_time < point:
                        covs.append(count)
                        break
                last_time = time
        for idx, point in enumerate(POINTS):
            df.loc[point, 'libxml2'] = covs[idx]
        dfs[fuzzer] = df
    correct_dfs.append(dfs)

for i in range(1, 6):
    with pd.ExcelWriter(os.path.join(reps_dir, f'rep{i}.xlsx')) as writer:
        for fuzzer in FUZZERS:
            correct_dfs[i - 1][fuzzer].to_excel(writer, sheet_name=fuzzer)
