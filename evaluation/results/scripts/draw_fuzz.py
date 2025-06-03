import os.path
import sys
import matplotlib.pyplot as plt
import pandas as pd

methods = [
    ('elm', 'ELFuzz'),
    ('grmr', 'Grammarinator + ANTLR4'),
    ('isla', 'ISLa + ANTLR4'),
    ('islearn', 'ISLa + ANTLR4 + ISLearn'),
    # ('alt', 'ELMFuzz-noFS')
]

benchmarks = [
    ('jsoncpp', 'jsoncpp'), ('libxml2', 'libxml2'), ('re2', 're2'), ('sqlite3', 'SQLite'),
    # ('cpython3', 'CPython'), 
    ('cvc5', 'cvc5'), ('librsvg', 'librsvg')
]

excludes = set([('jsoncpp', 'islearn'), ('re2', 'islearn')])

fig, axs = plt.subplots(2, 3)

FILE = os.path.join(os.path.dirname(__file__), '..', 'rq1', 'fuzz.xlsx')

x = [600, 1200, 1800, 2400, 3000, 3600]
for (b, b_name), ax in zip(benchmarks, axs.flat):
    ax.set_title(b_name)
    df = pd.read_excel(FILE, header=0, sheet_name=f'{b}')
    for m, m_name in methods:
        if (b, m) in excludes:
            continue
        y = df[m].to_list()
        # y.insert(0, 0)
        
        diff = []
        for i in range(1, len(y)):
            diff.append(y[i] - y[i - 1])
        
        ax.plot(x[1:], diff, '.-', label=m_name)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Edge coverage diff')
handles, labels = plt.gca().get_legend_handles_labels()
fig.legend(handles, labels, loc='upper right')
plt.show()
