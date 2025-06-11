import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib
import numpy as np
import pandas as pd
import matplotlib.ticker as ticker
import os
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42

PWD = os.path.dirname(os.path.abspath(__file__))

class ScalarFormatterForceFormat(ticker.ScalarFormatter):
    def _set_format(self):  # Override function that finds format to use.
        self.format = "%1.1f"  # Give format here

BENCHMARKS = [
              ('libxml2', 'libxml2', 20), 
              ('sqlite3', 'SQLite', 40), 
              ('cpython3', 'CPython', 4), 
            ]

FUZZERS = [('elm', 'ELFuzz', '#A9C4EB', '////'), ('grmr', 'Grmr', '#D5E8D4', '\\\\\\\\'), 
           ('isla', 'ISLa', '#F7C3EB', '....'), ('islearn', 'ISLearn', '#F8CECC', 'xxxx'),
           ('glade', 'GLADE', '#FEE69D', '****')]

df = pd.read_excel(os.path.join(PWD, "data", "unique.xlsx"), index_col=0, header=0)

data = {
    'libxml2': {'elm': df.loc['libxml2', 'elm'], 'grmr': df.loc['libxml2', 'grmr'], 'isla': df.loc['libxml2', 'isla'], 'islearn': df.loc['libxml2', 'islearn'], 'glade': df.loc['libxml2', 'glade']},
    'sqlite3': {'elm': df.loc['sqlite3', 'elm'], 'grmr': df.loc['sqlite3', 'grmr'], 'isla': df.loc['sqlite3', 'isla'], 'islearn': df.loc['sqlite3', 'islearn'], 'glade': df.loc['sqlite3', 'glade']},
    'cpython3': {'elm': df.loc['cpython3', 'elm'], 'grmr': df.loc['cpython3', 'grmr'], 'isla': df.loc['cpython3', 'isla'], 'islearn': df.loc['cpython3', 'islearn'], 'glade': df.loc['cpython3', 'glade']},
}

if __name__ == '__main__':
    plt.rcParams.update({'font.size': 9})
    plt.rcParams.update({'font.family': 'Times New Roman'})
    plt.rcParams.update({'hatch.linewidth': 0.1})
    plt.rcParams.update({'axes.linewidth': 0.2})
    plt.rcParams.update({'ytick.major.width': 0.1})
    plt.rcParams.update({'ytick.minor.width': 0.1})
    grid = gridspec.GridSpec(1, 4, wspace=0.3, hspace=0)
    fig = plt.figure(figsize=(6, 1*15/12))
    axs = {
        'libxml2': fig.add_subplot(grid[0, 0]),
        'cpython3': fig.add_subplot(grid[0, 1]),
        'sqlite3': fig.add_subplot(grid[0, 2]),
    }
    for benchmark, name, yscale in BENCHMARKS:
        data_list = []
        for fuzzer, label, color, hatch in FUZZERS:
            data_list.append(data[benchmark][fuzzer])
        axs[benchmark].bar([fuzzer for fuzzer, _, _, _ in FUZZERS], 
                           data_list, 
                           color=[color for _, _, color, _ in FUZZERS], 
                           hatch=[hatch for _, _, _, hatch in FUZZERS],
                           label=[label for _, label, _, _ in FUZZERS],
                           linewidth=0.1, edgecolor='black', zorder=3)
        box = axs[benchmark].get_position()
        axs[benchmark].set_title(name, y=1.05)
        axs[benchmark].set_position([box.x0, box.y0 + box.height * 0.25,
                 box.width, box.height * 0.6383])
        axs[benchmark].xaxis.set_ticks_position('none')
        axs[benchmark].xaxis.set_major_formatter(plt.NullFormatter())
        major_interval = yscale / 2
        minor_interval = yscale / 4
        
        major_ticks = []
        current = 0
        while current <= data[benchmark]['elm']:
            major_ticks.append(current)
            current += major_interval
        minor_ticks = []
        current = 0
        while current <= data[benchmark]['elm']:
            if current not in major_ticks:
                minor_ticks.append(current)
            current += minor_interval
    
        axs[benchmark].set_yticks(major_ticks)
        axs[benchmark].set_yticks(minor_ticks, minor=True)
    
        axs[benchmark].yaxis.grid(which='both', linestyle='-', linewidth=0.5, zorder=0)
        
        if benchmark == 'libxml2':
            axs[benchmark].set_ylabel('Unique bugs')
            axs[benchmark].set_xlabel('   ')
        
    lines, labels = axs['libxml2'].get_legend_handles_labels()
    fig.legend(lines, labels, loc='upper center', ncol=1, bbox_to_anchor=(0.82, 0.96))
    fig.tight_layout()
    fig.savefig(os.path.join(PWD, 'fig', 'unique.pdf'), bbox_inches='tight')