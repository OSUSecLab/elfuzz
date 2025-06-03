import pandas as pd
import os

PWD = os.path.realpath(os.path.dirname(__file__))

input_file = os.path.join(PWD, "data", "rq1_sum.xlsx")

BENCHMARKS = ["jsoncpp", "re2", "sqlite3", "cpython3", "libxml2", "librsvg", "cvc5"]

FUZZER = "elm"

OTHER_FUZZERS = ["grmr", "glade", "isla", "islearn"]

max_promotion = 0

for benchmark in BENCHMARKS:
    df = pd.read_excel(input_file, sheet_name=benchmark, header=0, index_col=0)
    elm_cov = df.loc[24, FUZZER]
    for fuzzer in OTHER_FUZZERS:
        cov = df.loc[24, fuzzer]
        promotion = (elm_cov - cov) / cov
        if promotion > max_promotion:
            max_promotion = promotion
            max_promotion_fuzzer = fuzzer

print(f"{FUZZER} {max_promotion_fuzzer} {max_promotion}")