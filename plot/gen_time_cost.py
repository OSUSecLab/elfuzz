import pandas as pd
import os

PWD = os.path.dirname(os.path.abspath(__file__))

latex = r"""\begin{table}[t]
    \centering
    \scriptsize
    \begin{tabularx}{\linewidth}{Xr@{\hspace{1.2em}}r@{\hspace{1.2em}}r@{\hspace{1.2em}}r@{\hspace{1.2em}}r@{\hspace{1.2em}}r@{\hspace{1.2em}}r}
        \toprule
         \textbf{Fuzzer} & \texttt{jsoncpp} & \texttt{libxml2} & \texttt{re2} & \texttt{CPython} & \texttt{SQLite} & \texttt{cvc5} & \texttt{librsvg} \\
         \midrule
"""

BENCHMARKS = ["jsoncpp", "libxml2", "re2", "cpython3", "sqlite3", "cvc5", "librsvg"]
FUZZERS = [("elm", "ELFuzz"), ("islearn", "ISLearn"), ("glade", "GLADE")]

df = pd.read_csv(os.path.join(PWD, "data", "x_record_second.csv"), index_col=0, header=0)

for fuzzer, fuzzer_name in FUZZERS:
    line = r"\textsc{" + fuzzer_name + r"}"
    for benchmark in BENCHMARKS:
        if benchmark == "jsoncpp" and fuzzer == "islearn":
            line += r" & N/A "
            continue
        value = df.loc[benchmark, fuzzer] / 3600 # type: ignore
        digits = 3
        try_format_str = f"%.{digits}f"
        try_format = try_format_str % value
        while len(try_format) > 4:
            digits -= 1
            try_format_str = f"%.{digits}f"
            try_format = try_format_str % value
        line += r" & " + try_format
    line += r" \\"
    latex += line + "\n"

latex += r"""    \bottomrule
    \end{tabularx}
    \caption{Time cost of synthesis (h)}
    \label{tab:time_cost}
\end{table}
"""

with open(os.path.join(PWD, "table", "time_cost.tex"), "w") as f:
    f.write(latex)
