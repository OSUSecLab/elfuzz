import matplotlib.pyplot as plt
import os.path
import pandas as pd
import sys

mode = sys.argv[1]

FILE = os.path.join(os.path.dirname(__file__), '..', 'rq3', 'fs.xlsx')

benchmarks = [
    ('libxml2', 'libxml2'), ('re2', 're2'), ('sqlite3', 'SQLite'), ('cpython3', 'CPython'),
    ('cvc5', 'cvc5'), ('librsvg', 'librsvg')
]

fig, axs = plt.subplots(2, 3)

for (b, name), ax in zip(benchmarks, axs.flat):
    df = pd.read_excel(FILE, header=0, sheet_name=b)

    gen = df['gen']
    fs_size=  [df['fs_size'], df['fs_size_alt']]
    max_cov = [df['max_cov'], df['max_cov_alt']]
    
    match mode:
        case 'fs':
            y1 = fs_size[0]
            y2 = fs_size[1]
        case 'cov':
            y1 = max_cov[0]
            y2 = max_cov[1]
    
    ax.set_title(name)
    ax.set_xlabel('Generation')
    ax.set_ylabel('Size of fuzzer space')
    ax.plot(gen, y1, 'b.-', label='ELMFuzz')
    ax.plot(gen, y2, 'r.-', label='ELMFuzz-noFS')
# plt.legend(loc='upper right')
handles, labels = plt.gca().get_legend_handles_labels()
fig.legend(handles, labels, loc='upper right')
plt.show()
