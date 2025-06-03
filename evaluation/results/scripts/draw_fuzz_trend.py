import click
import os
from os import path
import pandas
import matplotlib.pyplot as plt
import numpy as np
# from mpl_toolkits.axes_grid1 import make_axes_locatable
from brokenaxes import brokenaxes
import matplotlib.gridspec as gridspec

FUZZERS = [
    ('elm', 'ELFuzz'),
    ('alt', 'ELFuzz-noFS'),
    ('grmr', 'Grammarinator + ANTLR4'),
    ('isla', 'ISLa + ANTLR4'),
    ('islearn', 'ISLa + ANTLR4 + ISLearn')
]

BENCHMARKS = [
    'libxml2',
    're2',
    'cpython3',
    'sqlite3',
    'cvc5',
    'librsvg'
]

EXCLUDES = [('re2', 'islearn')]

POINTS = [0, 600, 1200, 1800, 2400, 3000, 3600]

@click.command()
@click.option('--input', '-i', required=True, help='Input directory', 
              type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.option('--output', '-o', required=False, help='Output file',
              type=click.Path(dir_okay=False, file_okay=True, exists=False), default='-')
@click.option('--repeat', '-r', type=int, required=False, default=5)
def main(input, output, repeat):
    data = []
    
    for i in range(1, repeat + 1):
        rep_data = {}
        f = path.join(input, f'rep{i}.xlsx')
        for fuzzer, _ in FUZZERS:
            df = pandas.read_excel(f, sheet_name=fuzzer, header=0, index_col=0)
            for benchmark in BENCHMARKS:
                if (benchmark, fuzzer) in EXCLUDES:
                    continue
                if benchmark not in rep_data:
                    rep_data[benchmark] = {}
                counts = list(df.loc[:, benchmark].values)
                assert len(counts) == len(POINTS)
                rep_data[benchmark][fuzzer] = counts
        data.append(rep_data)
    
    avg_data = {}
    errors = {}
    for benchmark in BENCHMARKS:
        avg_data[benchmark] = {}
        errors[benchmark] = {}
        for fuzzer, _ in FUZZERS:
            if (benchmark, fuzzer) in EXCLUDES:
                continue
            to_avg = [
                data[i][benchmark][fuzzer]
                for i in range(repeat)
            ]
            avg = list(np.mean(to_avg, axis=0))
            avg_data[benchmark][fuzzer] = avg
            lower_errors = list(avg - np.min(to_avg, axis=0))
            upper_errors = list(np.max(to_avg, axis=0) - avg)
            errors[benchmark][fuzzer] = (lower_errors, upper_errors)

    gss = gridspec.GridSpec(2, 3)

    ### CVC5

    for benchmark, gs in zip(BENCHMARKS, [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]):
        gs = gss[gs[0], gs[1]]
        match benchmark:
            case 'cvc5':
            
                min_elm_y = min([avg_data[benchmark]['elm'][i] - errors[benchmark]['elm'][0][i] for i in range(len(POINTS))])
                max_elm_y = max([avg_data[benchmark]['elm'][i] + errors[benchmark]['elm'][1][i] for i in range(len(POINTS))])

                min_alt_y = min([avg_data[benchmark]['alt'][i] - errors[benchmark]['alt'][0][i] for i in range(len(POINTS))])
                max_alt_y = max([avg_data[benchmark]['alt'][i] + errors[benchmark]['alt'][1][i] for i in range(len(POINTS))])
                
                min_other_y = min([avg_data[benchmark][fuzzer][i] - errors[benchmark][fuzzer][0][i] 
                                   for fuzzer, _ in FUZZERS for i in range(len(POINTS)) 
                                   if fuzzer in avg_data[benchmark] and fuzzer not in ['elm', 'alt']])
                max_other_y = max([avg_data[benchmark][fuzzer][i] + errors[benchmark][fuzzer][1][i] 
                                for fuzzer, _ in FUZZERS for i in range(len(POINTS)) 
                                if fuzzer in avg_data[benchmark] and fuzzer not in ['elm', 'alt']])
                margin = 250
                bax = brokenaxes(xlims=((0, 3700),), 
                                 ylims=((min_other_y - margin, max_other_y + margin), 
                                        (min_alt_y - margin, max_alt_y + margin), 
                                        (min_elm_y - margin, max_elm_y + margin)), 
                                 subplot_spec=gs)
                bax.set_title(benchmark)
                for fuzzer, label in FUZZERS:
                    if fuzzer not in avg_data[benchmark]:
                        continue
                    bax.errorbar(POINTS, avg_data[benchmark][fuzzer], yerr=errors[benchmark][fuzzer], label=label)
                bax.legend()
            case 'sqlite3':
                min_elm_y = min([avg_data[benchmark]['elm'][i] - errors[benchmark]['elm'][0][i] for i in range(len(POINTS))])
                max_elm_y = max([avg_data[benchmark]['elm'][i] + errors[benchmark]['elm'][1][i] for i in range(len(POINTS))])

                min_alt_grmr_y = min([avg_data[benchmark][fuzzer][i] - errors[benchmark][fuzzer][0][i]
                                      for fuzzer in ['alt', 'grmr']
                                      for i in range(len(POINTS))])
                max_alt_grmr_y = max([avg_data[benchmark][fuzzer][i] + errors[benchmark][fuzzer][1][i]
                                      for fuzzer in ['alt', 'grmr']
                                      for i in range(len(POINTS))])
                print(max_alt_grmr_y)
                
                min_other_y = min([avg_data[benchmark][fuzzer][i] - errors[benchmark][fuzzer][0][i]
                                for fuzzer, _ in FUZZERS for i in range(len(POINTS)) 
                                if fuzzer in avg_data[benchmark] and fuzzer not in ['elm', 'alt', 'grmr']])
                max_other_y = max([avg_data[benchmark][fuzzer][i] + errors[benchmark][fuzzer][1][i]
                                for fuzzer, _ in FUZZERS for i in range(len(POINTS)) 
                                if fuzzer in avg_data[benchmark] and fuzzer not in ['elm', 'alt', 'grmr']])
                margin = 250
                bax = brokenaxes(xlims=((0, 3700),), 
                                 ylims=((min_other_y - margin, max_other_y + margin), 
                                        (min_alt_grmr_y - margin, max_alt_grmr_y + margin), 
                                        (min_elm_y - margin, max_elm_y + margin)), 
                                 subplot_spec=gs)
                bax.set_title(benchmark)
                for fuzzer, label in FUZZERS:
                    if fuzzer not in avg_data[benchmark]:
                        continue
                    bax.errorbar(POINTS, avg_data[benchmark][fuzzer], yerr=errors[benchmark][fuzzer], label=label)
                bax.legend()
            case _:
                ax = plt.subplot(gs)
                ax.set_title(benchmark)
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Coverage')
                for fuzzer, label in FUZZERS:
                    if (benchmark, fuzzer) in EXCLUDES:
                        continue
                    ax.errorbar(POINTS, avg_data[benchmark][fuzzer], yerr=errors[benchmark][fuzzer], label=label)
                ax.legend()
    
    # fig, axs = plt.subplots(2, len(BENCHMARKS) // 2)
    # for benchmark, ax in zip(BENCHMARKS, axs.flatten()):
    #     match benchmark:
    #         case 'cvc5':
    #             devider = make_axes_locatable(ax)
    #             ax_top = ax
    #             ax_bottom = devider.append_axes('bottom', size='100%', pad=0.1)
    #             fig.add_axes(ax_bottom)
    #             # tmp, (ax_top, ax_bottom) = subfig.subfigures(2, 1, sharex=True)
    #             ax_top.errorbar(POINTS, avg_data[benchmark]['elm'], yerr=errors[benchmark]['elm'], label='ELFuzz')
    #             for fuzzer, label in [item for item in FUZZERS if item[0] != 'elm']:
    #                 ax_bottom.errorbar(
    #                     POINTS,
    #                     avg_data[benchmark][fuzzer],
    #                     yerr=errors[benchmark][fuzzer],
    #                     label=label
    #                 )
                    
    #         case _:
    #             ax.set_title(benchmark)
    #             ax.set_xlabel('Time (s)')
    #             ax.set_ylabel('Coverage')
    #             for fuzzer, label in FUZZERS:
    #                 if (benchmark, fuzzer) in EXCLUDES:
    #                     continue
    #                 ax.errorbar(
    #                     POINTS,
    #                     avg_data[benchmark][fuzzer],
    #                     yerr=errors[benchmark][fuzzer],
    #                     label=label
    #                 )
    #             ax.legend()
    # # plt.tight_layout()
    # plt.
    plt.show()
    
if __name__ == '__main__':
    main()