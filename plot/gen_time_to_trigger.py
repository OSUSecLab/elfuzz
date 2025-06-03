import pandas as pd
import os

PWD = os.path.dirname(os.path.abspath(__file__))

FUZZERS = [("elm", "ELFuzz"), ("grmr", "Grmr"), ("isla", "ISLa"), ("islearn", "ISLearn"), ("glade", "GLADE")]
# FUZZERS = [("elm", "ELFuzz"), ("grmr", "Grammarinator"), ("isla", "ISLa"), ("islearn", "ISLearn")]
BENCHMARKS = ["libxml2", "cpython3", "sqlite3"]

data = {}

for benchmark in BENCHMARKS:
    df = pd.read_excel(os.path.join(PWD, "data", f"rq2_time_to_trigger.xlsx"), sheet_name=benchmark, header=0, index_col=0)
    for fuzzer, _ in FUZZERS:
        if benchmark not in data:
            data[benchmark] = {}
        if fuzzer not in data[benchmark]:
            data[benchmark][fuzzer] = []
        for q in [0.25, 0.5, 0.75]:
            v = df.loc[q, fuzzer] # type: ignore
            try:
                to_add = float(v)
            except:
                to_add = -1
            data[benchmark][fuzzer].append(to_add)

to_emphsize = set()
second_best = {}

for benchmark, obj in data.items():
    if benchmark not in second_best:
        second_best[benchmark] = []
    for i in range(3):
        min = float("inf")
        second_min = float("inf")
        for fuzzer, values in obj.items():
            if values[i] > 0 and values[i] < min:
                min = values[i]
            if values[i] > 0 and values[i] < second_min and values[i] > min:
                second_min = values[i]
        min_count = 0
        for fuzzer, values in obj.items():
            if min > 0 and values[i] == min:
                min_count += 1
                to_emphsize.add((benchmark, fuzzer, i))
        if min_count <= 1:
            second_best[benchmark].append(second_min)
        else:
            second_best[benchmark].append(min)

lines = ""
for fuzzer, fuzzer_name in FUZZERS:
    line = f"        \\textsc{{{fuzzer_name}}}"
    for benchmark in BENCHMARKS:
        values = data[benchmark][fuzzer]
        for i in range(3):
            if values[i] < 0:
                line += r" & $\infty$"
            elif (benchmark, fuzzer, i) in to_emphsize:
                line += r" & \textbf{" + f"{values[i]:.0f}" + "}"
            else:
                line += r" & " + f"{values[i]:.0f}"
    line += r" \\"
    lines += line + "\n"

lines += "        \\midrule\n"

lines += r"        Speedup"
for benchmark in BENCHMARKS:
    for i in range(3):
        elm_value = data[benchmark]["elm"][i]
        second_best_value = second_best[benchmark][i]
        if second_best_value == -1:
            lines += r" & N/A"
        elif elm_value == second_best_value:
            lines += r" & " + f"1.0x"
        else:
            lines += r" & " + f"{(second_best_value / elm_value):.1f}x"
lines += r" \\"

HEAD = r"""\begin{table}[t]
    \centering
        \scriptsize
    \begin{tabularx}{\linewidth}{l*9{>{\raggedleft\arraybackslash}X}}
        \toprule
        \multirow{2}[2]{*}{\textbf{Fuzzer}} & \multicolumn{3}{r}{\textbf{libxml2}} & \multicolumn{3}{r}{}\textbf{CPython} & \multicolumn{3}{r}{\textbf{SQLite}} \\ 
        \cmidrule(l){2-4} \cmidrule(l){5-7} \cmidrule(l){8-10}
        & 25\% & 50\% & 75\% & 25\% & 50\% & 75\% & 25\% & 50\% & 75\% \\
         \midrule
"""

TAIL = r"""         \bottomrule
    \end{tabularx}
    \caption{Time (min) to trigger 25\%, 50\%, and 75\% of all bugs that \textsc{ELFuzz} can trigger}
    \label{tab:time_quantile}
\end{table}
"""

with open(os.path.join(PWD, "table", "time_to_trigger.tex"), "w") as f:
    f.write(HEAD + lines + TAIL)