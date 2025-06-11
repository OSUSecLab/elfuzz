import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import os
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

FUZZERS = [('elm', 'ELFuzz', '#5A5BA0', '#A9C4EB', 's'), ('grmr', 'Grmr', '#009473', '#D5E8D4', 'o'), 
           ('isla', 'ISLa', '#F776DA', '#F7C3EB', 'v'), ('islearn', 'ISLearn', '#D95070', '#F8CECC', 'D'),
           ('glade', 'GLADE', '#EC9C42', '#FEE69D', '^')]

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
            data[fuzzer] = ([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24], [], [])
            # for i in range(1, 25):
            sequence = []
            with pd.ExcelFile(os.path.join(PLOT_DIR, 'data', 'rq1_sum.xlsx')) as xls:
                df = pd.read_excel(xls, benchmark, index_col=0, header=0)
                for time, cov in df[fuzzer].items():
                    if np.isnan(cov):
                        continue
                    # data[fuzzer][0].append(time)
                    sequence.append(int(cov))
            if len(sequence) != 25:
                print(f"Warning: {benchmark}_{fuzzer} {len(sequence)} {len(sequence)=}")
                continue
            assert len(sequence) == 25, f'{benchmark}_{fuzzer} {i} {len(sequence)} {len(sequence)=}'
            data[fuzzer][1].extend(sequence)
            with pd.ExcelFile(os.path.join(PLOT_DIR, 'data', 'rq1_std.xlsx')) as xls:
                df = pd.read_excel(xls, benchmark, index_col=0, header=0)
                for time, cov in df[fuzzer].items():
                    if np.isnan(cov):
                        continue
                    data[fuzzer][2].append(cov)

        for (fuzzer, label, color, fill_color, marker), ls in zip(reversed(FUZZERS), ['-.', '-', '--', (0, (1, 1)), '-']):
            if (benchmark, fuzzer) in EXCLUDE:
                continue
            mean = data[fuzzer][1]
            if len(mean) != 25:
                continue
            standard_deviation = data[fuzzer][2]
            upper_error = [mean[i] + standard_deviation[i] for i in range(len(mean))]
            lower_error = [mean[i] - standard_deviation[i] for i in range(len(mean))]
            match fuzzer:
                case 'islearn':
                    linewidth = 2.4
                    zorder = 10
                case 'isla':
                    linewidth = 1.6
                    zorder = 11
                case 'grmr':
                    linewidth = 1.3
                    zorder = 12
                case 'glade':
                    linewidth = 2
                    zorder = 10.5
                case 'elm':
                    linewidth = 1.3
                    zorder = 13
            axs[benchmark].plot(data[fuzzer][0], mean, label=label, color=color, marker= "v" if fuzzer=='elm' else None, markersize=2.6,
                                markevery=[0, 3, 6, 9, 12, 15, 18, 21, 24], linewidth=linewidth, ls=ls, zorder=zorder,
                                alpha=0.8 if fuzzer == 'elm' and benchmark in ['jsoncpp', 're2'] else 1)
            axs[benchmark].fill_between(data[fuzzer][0],
                                        lower_error, 
                                        upper_error, 
                                        alpha=0.7,
                                        zorder=zorder-10,
                                        color=fill_color,
                                        edgecolor='face')
        
        max_y = max(mean + std for mean, std in zip(data['elm'][1], data['elm'][2]))
        # min_y = min(min(mean - std for mean, std in zip(data[fuzzer][1], data[fuzzer][2])) for fuzzer, _, _, _, _ in FUZZERS if (benchmark, fuzzer) not in EXCLUDE)
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
        # axs[benchmark].set_ylim(bottom=min_y)
        # axs[benchmark].grid(axis='y', linestyle='-', linewidth=0.5, zorder=0, which='both')
        
        yfmt = ScalarFormatterForceFormat()
        yfmt.set_powerlimits((0, 0))
        axs[benchmark].yaxis.set_major_formatter(yfmt)
        axs[benchmark].set_xticks([
            0, 6, 12, 18, 24
        ])
        axs[benchmark].set_xticks([
            3, 9, 15, 21
        ], minor=True)
        axs[benchmark].grid(True, which='both', linestyle='-', linewidth=0.5)
        match benchmark:
            case 'sqlite3':
                axs[benchmark].set_xlabel('Time (h)')
                axs[benchmark].set_ylabel('Covered edges')
        box = axs[benchmark].get_position()
        axs[benchmark].set_position([box.x0, box.y0 + box.height * 0.2,
                 box.width, box.height * 0.8])
    lines, labels = axs['libxml2'].get_legend_handles_labels()
    # for line in lines:
    #     line.set_linewidth(1)
    from copy import deepcopy
    copied_lines = deepcopy(lines)
    for line in copied_lines:
        line.set_alpha(1)
        line.set_linewidth(1.3) # type: ignore
    ax = fig.get_axes()[0]
    box = ax.get_position()
    fig.legend(list(reversed(copied_lines)), list(reversed(labels)), loc='upper center', ncol=1, bbox_to_anchor=(0.825, 0.5))
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, 'fig', 'cov_trends_during.pdf'), bbox_inches='tight')
