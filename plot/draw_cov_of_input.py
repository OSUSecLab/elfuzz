import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib
import numpy as np
import pandas as pd
import matplotlib.ticker as ticker
import os
import matplotlib.font_manager as fm
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42

PLOT_DIR = os.path.dirname(os.path.abspath(__file__))

class ScalarFormatterForceFormat(ticker.ScalarFormatter):
    def _set_format(self):  # Override function that finds format to use.
        self.format = "%1.1f"  # Give format here

HOLD = []

BENCHMARKS = [('jsoncpp', 'jsoncpp', 1e2),
              ('libxml2', 'libxml2', 1e3),
              ('re2', 're2', 1e3),
              ('cpython3', 'CPython', 1e4),
              ('cvc5', 'cvc5', 1e4),
              ('sqlite3', 'SQLite', 1e4),
              ('librsvg', 'librsvg', 1e4)
            ]

FUZZERS = [('elm', 'ELFuzz', '#A9C4EB', '////'), ('grmr', 'Grmr', '#D5E8D4', '\\\\\\\\'),
           ('isla', 'ISLa', '#F7C3EB', '....'), ('islearn', 'ISLearn', '#F8CECC', 'xxxx'),
            ('glade', 'GLADE', '#FEE69D', '****')]

EXCLUDE = [('jsoncpp', 'islearn'), ('re2', 'islearn')]

if __name__ == '__main__':
    plt.rcParams.update({'font.size': 9})
    plt.rcParams.update({'font.family': 'Times New Roman'})
    plt.rcParams.update({'hatch.linewidth': 0.1})
    plt.rcParams.update({'axes.linewidth': 0.2})
    plt.rcParams.update({'ytick.major.width': 0.1})
    plt.rcParams.update({'ytick.minor.width': 0.1})
    grid = gridspec.GridSpec(2, 4, wspace=0.3, hspace=0.2)
    fig = plt.figure(figsize=(6, 2))
    axs = {
        'jsoncpp': fig.add_subplot(grid[0, 0]),
        'libxml2': fig.add_subplot(grid[0, 1]),
        're2': fig.add_subplot(grid[0, 2]),
        'cpython3': fig.add_subplot(grid[0, 3]),
        'sqlite3': fig.add_subplot(grid[1, 0]),
        'cvc5': fig.add_subplot(grid[1, 1]),
        'librsvg': fig.add_subplot(grid[1, 2]),
    }

    for benchmark, name, exp_scale in BENCHMARKS:
        if benchmark in HOLD:
            continue
        with pd.ExcelFile(os.path.join(PLOT_DIR, 'data', 'seed_cov.xlsx')) as xls:
            df = pd.read_excel(xls, benchmark, index_col=0, header=0)
            data = {}
            for fuzzer, _, _, _ in FUZZERS:
                if (benchmark, fuzzer) in EXCLUDE:
                    continue
                data[fuzzer] = ([], [])
                for time, cov in df[fuzzer].items():
                    if np.isnan(cov):
                        continue
                    data[fuzzer][0].append(time)
                    data[fuzzer][1].append(int(cov))
        values = []
        for fuzzer, label, color, _ in FUZZERS:
            if (benchmark, fuzzer) in EXCLUDE:
                values.append(0)
                continue
            values.append(data[fuzzer][1][-1])
        max_y = max(values)
        max_y_i = max_y // exp_scale
        interval = max_y_i / 4
        all_ticks = []
        current = 0
        while current * interval * exp_scale < max_y:
            all_ticks.append(current * interval * exp_scale)
            current += 1
        major_ticks = []
        minor_ticks = []
        tick_labels = []
        for i, tick in enumerate(all_ticks):
            if i % 2 == 0:
                major_ticks.append(tick)
            else:
                minor_ticks.append(tick)

        axs[benchmark].grid(axis='y', linestyle='-', linewidth=0.5, zorder=0, which='both')
        axs[benchmark].bar([0, 1, 2, 3, 4], values,
                           color=[color for _, _, color, _ in FUZZERS],
                           label=[label for _, label, _, _ in FUZZERS],
                           hatch=[hatch for _, _, _, hatch in FUZZERS],
                           linewidth=0.1, edgecolor='black', zorder=3)
        axs[benchmark].set_yticks(major_ticks)
        axs[benchmark].set_yticks(minor_ticks, minor=True)
        axs[benchmark].set_title(name, loc='center')
        yfmt = ScalarFormatterForceFormat()
        yfmt.set_powerlimits((0, 0))
        axs[benchmark].xaxis.set_ticks_position('none')
        axs[benchmark].xaxis.set_major_formatter(plt.NullFormatter())
        axs[benchmark].yaxis.set_major_formatter(yfmt)
        match benchmark:
            case 'sqlite3':
                axs[benchmark].set_ylabel('Covered edges')
        box = axs[benchmark].get_position()
        axs[benchmark].set_position([box.x0, box.y0 + box.height * 0.2,
                 box.width, box.height * 0.8])
    lines, labels = axs['libxml2'].get_legend_handles_labels()
    fig.legend(lines, labels, loc='upper center', ncol=1, bbox_to_anchor=(0.825, 0.58))
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, 'fig', 'cov_of_input.pdf'), bbox_inches='tight')
