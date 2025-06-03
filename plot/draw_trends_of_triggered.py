import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib
import numpy as np
import pandas as pd
import os

PWD = os.path.dirname(os.path.abspath(__file__))

HOLD = []

BENCHMARKS = [
              ('libxml2', 'libxml2', 200),
              ('sqlite3', 'SQLite', 40),
              ('cpython3', 'CPython', 50),
            ]

FUZZERS = [('elm', 'ELFuzz', '#5A5BA0', '#A9C4EB', 's'), ('grmr', 'Grmr', '#009473', '#D5E8D4', 'o'),
           ('isla', 'ISLa', '#F776DA', '#F7C3EB', 'v'), ('islearn', 'ISLearn', '#D95070', '#F8CECC', 'D'),
           ('glade', 'GLADE', '#FCAC51', '#FEE69D', 'x')]

EXCLUDE = [('re2', 'islearn'), ('jsoncpp', 'islearn')]

if __name__ == '__main__':
    plt.rcParams.update({'font.size': 9})
    plt.rcParams.update({'font.family': 'Times New Roman'})
    plt.rcParams.update({'hatch.linewidth': 0.1})
    plt.rcParams.update({'axes.linewidth': 0.2})
    plt.rcParams.update({'ytick.major.width': 0.1})
    plt.rcParams.update({'ytick.minor.width': 0.1})
    plt.rcParams.update({'xtick.major.width': 0.1})
    plt.rcParams.update({'xtick.minor.width': 0.1})
    grid = gridspec.GridSpec(1, 4, wspace=0.3, hspace=0)
    fig = plt.figure(figsize=(6, 15/12))
    axs = {
        'libxml2': fig.add_subplot(grid[0, 0]),
        'cpython3': fig.add_subplot(grid[0, 1]),
        'sqlite3': fig.add_subplot(grid[0, 2]),
    }
    TIMEPOINTS = [i for i in range(25)]

    for benchmark, name, yscale in BENCHMARKS:
        if benchmark in HOLD:
            continue
        data = {}
        for fuzzer, _, _, _, _ in FUZZERS:
            if (benchmark, fuzzer) in EXCLUDE:
                continue
            data[fuzzer] = (TIMEPOINTS, [], [])
            sequence = pd.read_excel(os.path.join(PWD, f"data", f"rq2_count_bug.xlsx"), sheet_name=benchmark, header=0, index_col=0).loc[:, fuzzer]
            data[fuzzer][1].extend(sequence)
            
            std = pd.read_excel(os.path.join(PWD, f"data", f"rq2_std.xlsx"), sheet_name=benchmark, header=0, index_col=0).loc[:, fuzzer]
            data[fuzzer][2].extend(std)
        for fuzzer, label, color, fill_color, marker in reversed(FUZZERS):
            if (benchmark, fuzzer) in EXCLUDE:
                continue
            mean = data[fuzzer][1]
            upper_error = [mean[i] + data[fuzzer][2][i] for i in range(len(mean))]
            lower_error = [mean[i] - data[fuzzer][2][i] for i in range(len(mean))]
            axs[benchmark].plot(data[fuzzer][0], mean, label=label, color=color, marker=marker, markersize=3, markevery=3)
            axs[benchmark].fill_between(data[fuzzer][0],
                                        lower_error,
                                        upper_error,
                                        alpha=1,
                                        color=fill_color,
                                        edgecolor='face')
        axs[benchmark].set_title(name, y=1)
        axs[benchmark].set_xticks([0, 6, 12, 18, 24],)
        axs[benchmark].set_xticks([t for t in TIMEPOINTS if t % 6 != 0 and t % 3 == 0], minor=True)
        match benchmark:
            case "libxml2":
                major_yticks = [0, 100, 200]
                minor_yticks = [50, 150]
            case "cpython3":
                major_yticks = [0, 25, 50]
                minor_yticks = [12.5, 37.5]
            case "sqlite3":
                major_yticks = [0, 20, 40, 60]
                minor_yticks = [10, 30, 50]
        axs[benchmark].set_yticks(major_yticks)
        axs[benchmark].set_yticks(minor_yticks, minor=True)
        axs[benchmark].grid(True, linestyle='-', linewidth=0.5, zorder=0, which='both')
        match benchmark:
            case 'libxml2':
                axs[benchmark].set_xlabel('Time (h)')
                axs[benchmark].set_ylabel('Triggered bugs')
        box = axs[benchmark].get_position()
        axs[benchmark].set_position([box.x0, box.y0 + box.height * 0.25,
                 box.width, box.height * 0.6383])
    lines, labels = axs['cpython3'].get_legend_handles_labels()
    ax = fig.get_axes()[0]
    box = ax.get_position()
    fig.legend(reversed(lines), reversed(labels), loc='upper center', ncol=1, bbox_to_anchor=(0.82, 0.9))
    fig.tight_layout()
    fig.savefig(os.path.join(PWD, 'fig', 'trends_of_triggered.pdf'), bbox_inches='tight')
