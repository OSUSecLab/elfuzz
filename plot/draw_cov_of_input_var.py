import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib
import numpy as np
import pandas as pd
import matplotlib.ticker as ticker
import os

plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42

class ScalarFormatterForceFormat(ticker.ScalarFormatter):
    def _set_format(self):  # Override function that finds format to use.
        self.format = "%1.1f"  # Give format here

HOLD = []
PWD = os.path.dirname(os.path.abspath(__file__))

BENCHMARKS = [('jsoncpp', 'jsoncpp', 1e2), 
              ('libxml2', 'libxml2', 1e3), 
              ('re2', 're2', 1e3), 
              ('cpython3', 'CPython', 1e4), 
              ('cvc5', 'cvc5', 1e4), 
              ('sqlite3', 'SQLite', 1e4), 
              ('librsvg', 'librsvg', 1e4)
            ]

# FUZZERS = [('elm', 'ELFuzz', '#5A5BA0'), ('grmr', 'Grammarinator', '#009473'), 
#            ('isla', 'ISLa', '#FFCFAB'), ('islearn', 'ISLa + ISLearn', '#D95070')]

FUZZERS = [('elm', 'ELFuzz', '#A9C4EB', '////'), ('alt', 'ELFuzz-noFS', '#D5E8D4', '\\\\\\\\'), 
           ('nospl', 'ELFuzz-noSP', '#F7C3EB', '....'), ('nocomp', 'ELFuzz-noCP', '#F8CECC', 'xxxx'),
           ('noinf', 'ELFuzz-noIN', '#FEE69D', '****')]

EXCLUDE = [('re2', 'islearn')]

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
    
    # extra = fig.add_subplot(grid[1, 3])

    for benchmark, name, exp_scale in BENCHMARKS:
        if benchmark in HOLD:
            continue
        with pd.ExcelFile(os.path.join(PWD, 'data', 'rq3_ablation.xlsx')) as xls:
            df = pd.read_excel(xls, index_col=0, header=0)
            data = {}
            for fuzzer, _, _, _ in FUZZERS:
                if (benchmark, fuzzer) in EXCLUDE:
                    continue
                data[fuzzer] = ([], [])
                # for time, cov in df[fuzzer].items():
                #     if np.isnan(cov):
                #         continue
                #     data[fuzzer][0].append(time)
                #     data[fuzzer][1].append(int(cov))
                data[fuzzer][0].append(600)
                data[fuzzer][1].append(int(df.loc[benchmark, fuzzer]))
        values = []
        for fuzzer, label, color, _ in FUZZERS:
            if (benchmark, fuzzer) in EXCLUDE:
                values.append(0)
                continue
            values.append(data[fuzzer][1][-1])
        max_y = max(values)
        max_y_i = max_y // exp_scale
        interval = max_y_i / 4
        # ticks = [i * interval * exp_scale for i in range(5)]
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
                # tick_labels.append(f'{tick/exp_scale:.1f}')
                major_ticks.append(tick)
            else:
                minor_ticks.append(tick)
                # tick_labels.append('')
        # ticks = [0, max_y / 4, max_y /2, max_y max_y]
        # print(tick_labels)
        
        axs[benchmark].grid(axis='y', linestyle='-', linewidth=0.5, zorder=0, which='both')
        axs[benchmark].bar([0, 1, 2, 3, 4], values, 
                           color=[color for _, _, color, _ in FUZZERS],
                           label=[label for _, label, _, _ in FUZZERS],
                           hatch=[hatch for _, _, _, hatch in FUZZERS],
                           linewidth=0.1, edgecolor='black', zorder=3)
        axs[benchmark].set_yticks(major_ticks)
        axs[benchmark].set_yticks(minor_ticks, minor=True)
        # axs[benchmark].set_yticklabels(tick_labels)
        # bars = axs[benchmark].patches
        # for i in range(len(bars)):
        #     hatch = FUZZERS[i][3]
        #     bars[i].set_hatch(hatch)
        axs[benchmark].set_title(name, loc='center')
        yfmt = ScalarFormatterForceFormat()
        yfmt.set_powerlimits((0, 0))
        # turn off x ticks
        # axs[benchmark].axes.li
        # axs[benchmark].lines[1].set_linewidth(0.1)
        axs[benchmark].xaxis.set_ticks_position('none')
        axs[benchmark].xaxis.set_major_formatter(plt.NullFormatter())
        # axs[benchmark].yaxis.set_major_formatter(yfmt)
        axs[benchmark].yaxis.set_major_formatter(yfmt)
        match benchmark:
            case 'sqlite3':
                axs[benchmark].set_ylabel('Covered edges')
        box = axs[benchmark].get_position()
        axs[benchmark].set_position([box.x0, box.y0 + box.height * 0.2,
                 box.width, box.height * 0.8])
    lines, labels = axs['libxml2'].get_legend_handles_labels()
    # ax = fig.get_axes()[6]
    # box = grid.get_grid_positions(fig)[1, 3]
    # fig.legend(lines, labels, loc='upper center', ncol=1)
    # put legend to (1, 3)
    fig.legend(lines, labels, loc='upper center', ncol=1, bbox_to_anchor=(0.82, 0.57))
    fig.tight_layout()
    fig.savefig(os.path.join(PWD, 'fig', 'cov_of_input_var.pdf'), bbox_inches='tight')
