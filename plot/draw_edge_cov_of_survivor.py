import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
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

FUZZERS = [('elm', 'ELFuzz', '#5A5BA0', '#A9C4EB', 's'), ('alt', 'ELFuzz-noFS', '#009473', '#D5E8D4', 'o'), 
           ('nospl', 'ELFuzz-noSP', '#F776DA', '#F7C3EB', 'v'), ('nocomp', 'ELFuzz-noCP', '#D95070', '#F8CECC', 'D'),
           ('noinf', 'ELFuzz-noIN', '#FCAC51', '#FEE69D', '^')]

EXCLUDE = [('re2', 'islearn'), ('jsoncpp', 'islearn')]

if __name__ == '__main__':
    # plt.rcParams.update({'font.size': 9})
    # plt.rcParams.update({'font.family': 'Times New Roman'})
    plt.rcParams.update({'font.size': 9})
    plt.rcParams.update({'font.family': 'Times New Roman'})
    plt.rcParams.update({'hatch.linewidth': 0.1})
    plt.rcParams.update({'axes.linewidth': 0.2})
    plt.rcParams.update({'ytick.major.width': 0.1})
    plt.rcParams.update({'ytick.minor.width': 0.1})
    plt.rcParams.update({'xtick.major.width': 0.1})
    plt.rcParams.update({'xtick.minor.width': 0.1})
    grid = gridspec.GridSpec(2, 4, wspace=0.3, hspace=0.5)
    fig = plt.figure(figsize=(6, 2 * 15/12))
    # fig = plt.figure(figsize=(6, 2))
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
        data = {}
        for fuzzer, _, _, _, _ in FUZZERS:
            if (benchmark, fuzzer) in EXCLUDE:
                continue
            data[fuzzer] = (list(range(1, 51)), [])
            with pd.ExcelFile(os.path.join(PWD, 'data', 'rq3_evolve_cov.xlsx')) as xls:
                df = pd.read_excel(xls, benchmark, index_col=0, header=0)
                for i in range(1, 51):
                    data[fuzzer][1].append(df[fuzzer][i])
        for (fuzzer, label, color, _, marker), ls in zip(reversed(FUZZERS), ['-', '--', (0, (1, 1)), '-.', '-']):
            if (benchmark, fuzzer) in EXCLUDE:
                continue
            match fuzzer:
                case 'noinf':
                    linewidth = 2.4
                    zorder = 10
                case 'nocomp':
                    linewidth = 1.6
                    zorder = 11
                case 'nospl':
                    linewidth = 1.3
                    zorder = 12
                case 'alt':
                    linewidth = 2
                    zorder = 10.5
                case 'elm':
                    linewidth = 1.3
                    zorder = 13
            mean = [0] + data[fuzzer][1]
            axs[benchmark].plot(list(range(0, 51)), mean, label=label, color=color, markersize=2.6, 
                                marker='v' if fuzzer=='elm' else None, markevery=5, ls=ls, zorder=zorder, 
                                linewidth=linewidth, alpha=0.8 if fuzzer=='elm' else 1)
        axs[benchmark].set_title(name, y=1.1)
        
        max_y = data['elm'][1][-1]
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
        
        axs[benchmark].yaxis.set_ticks(major_ticks)
        axs[benchmark].yaxis.set_ticks(minor_ticks, minor=True)
        axs[benchmark].grid(axis='y', linestyle='-', linewidth=0.5, zorder=0, which='both')
        
        yfmt = ScalarFormatterForceFormat()
        yfmt.set_powerlimits((0, 0))
        axs[benchmark].yaxis.set_major_formatter(yfmt)
        x_ticks = [0, 25, 50]
        labels = ['0', '25', '50']
        axs[benchmark].set_xticks(x_ticks, labels)
        minor_ticks = [i * 5 for i in range(0, 11) if i * 5 not in x_ticks]
        axs[benchmark].set_xticks(minor_ticks, minor=True)
        axs[benchmark].grid(True, which='both', linestyle='-', linewidth=0.5)
        match benchmark:
            case 'sqlite3':
                axs[benchmark].set_xlabel('Evolution iteration')
                axs[benchmark].set_ylabel('Covered edges')
        box = axs[benchmark].get_position()
        axs[benchmark].set_position([box.x0, box.y0 + box.height * 0.2,
                 box.width, box.height * 0.8])
    lines, labels = axs['libxml2'].get_legend_handles_labels()
    ax = fig.get_axes()[0]
    from copy import deepcopy
    copied_lines = deepcopy(lines)
    for line in copied_lines:
        line.set_alpha(1)
        line.set_linewidth(1.3)
    box = ax.get_position()
    fig.legend(list(reversed(copied_lines)), list(reversed(labels)), loc='upper center', ncol=1, bbox_to_anchor=(0.82, 0.5))
    fig.tight_layout()
    fig.savefig(os.path.join(PWD, 'fig', 'edge_cov_of_survivor.pdf'), bbox_inches='tight')
