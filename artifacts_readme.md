# Replication Package of ELFuzz

[![Read on GitHub](https://img.shields.io/badge/Read%20on%20GitHub-OSUSecLab%2Felfuzz%3Aartifacts__readme.md-yellow)](https://github.com/OSUSecLab/elfuzz/blob/main/artifacts_readme.md)

## Overview

This Zenodo repository contains the replication package for the paper "ELFuzz: Efficient Input Generation via LLM-driven Synthesis Over Fuzzer Space." While this Zenodo repository is self-contained with all docs, code and data required to replicate the experiments, the original source code is hosted on [GitHub](https://github.com/OSUSecLab/elfuzz), where you may get a better reading experience for the docs.

The files are organized as follows:

- `elfuzz_src.tar.zst`: The source code of ELFuzz.
- `elfuzz_data_<timetag>.tar.zst.part<suffix>`: The experiment data.
- `elfuzz_docker_<timetag>.tar.zst.part<suffix>`: The Docker image to replicate the experiments.
- `elfuzz_baselines.tar.zst`: The source code of the baselines used in the experiments.
- `data_metadata.json`: Metadata information about the experiment data tarball.
- `docker_metadata.json`: Metadata information about the Docker image tarball.

You can download the data, source code, and Docker image tarballs and run the following command to combine the parts into a complete tarball:

```bash
cat "elffuzz_(data|docker)_<timetag>.tar.zst.part*" > "elffuzz_(data|docker|src)_<timetag>.tar.zst"
```

The source code tarball contains a `README.md` file that describes how to replicate the experiments.

Note that you need to install `zstd` to decompress the tarballs. On Ubuntu, use the following command to install it:

```bash
sudo apt install zstd
```

Decompress the data and source code tarballs to inspect their contents via the following command:

```bash
tar --zstd -xvf "elfuzz_(src|data)_<timetag>.tar.zst"
```

To use the Docker image tarball, you need to decompress and load it via the following command:

```bash
zstd -d "elfuzz_docker_<timetag>.tar.zst" -o "elfuzz_docker.tar"
docker load --input "elfuzz_docker.tar"
```

Follow the instructions in the `README.md` file in the source code tarball for later instructions to replicate the experiments using the Docker image.

In later sections, we will list the important contents of each tarball.

## Replicating the experiments

To replicate the experiments, please follow the instructions in the `README.md` file in the source code tarball.

## Contents of the Docker image tarball

This tarball contains a Docker image to replicate all the experiments and figures and tables in the paper.

## Contents of the ELFuzz source code tarball

This tarball contains the implementation of ELFuzz:

- `genvariants_parallel.py` implements the LLM-driven mutation.
- `getcov.py`, `getcov_fuzzbench.py`, and `select_seeds.py` implements the fuzzer space exploration and max-cover selection. `getcov.py` and `getcov_fuzzbench.py` approximate the cover set of a fuzzer candidate, and `select_seeds.py` constructs the cover space and selects the max-cover survivors.

Other files and directories are supportive components for the experiments. Some important ones are:

- `preset/` and `fuzzbench/` contains the configurations of the seven benchmarks.
- `start_tgi_servers.sh` launch a Hugging Face text-generation-inference (TGI) server to serve the LLM used in the experiments.
- `all_gen.sh` is the entry point of the whole evolution process.
- `plot/` contains scripts to generate the figures and tables in the paper.
- `cli/` provides a command-line interface for the users of the Docker image in the replication package.

## Contents of the baseline tarball

This tarball contains the source code of the three baselines (Grammarinator, GLADE, and ISLa/ISLearn) we used and the FixReverter bug-injection tool. We slightly modified the source code of GLADE and ISLa/ISLearn to add some CLI options and fix bugs. The commit hashes that the forked versions are based on are included in README files in the corresponding directories. Users should be able to inspect the modifications by diff tools. We also adapted the code of FixReverter to the benchmarks that we used in the experiments.

## Contents of the experiment data tarball

### Benchmark data

**Binaries for mutation-based fuzzing.** Binaries of the benchmarks that is used as fuzz targets in for the mutation-based fuzzing in RQ1 and RQ2 are in the `experiment_binaries` directory. The seven tarballs are for the seven benchmarks respectively: `jsoncpp.tar.zst`, `libxml2.tar.zst`, `re2.tar.zst`, `sqlite3.tar.zst` (for `SQLite`), `cpython3.tar.zst` (for `CPython`), `cvc5.tar.zst`, and `librsvg.tar.zst`.

**Binaries with injected bugs.** Binaries with injected bugs used in RQ2 are in the `misc/fr_injected` directory. `cpython3`, `libxml2`, and `sqlite3` contain the bug-injected binaries for `CPython`, `libxml2`, and `SQLite` respectively. Note that except the fuzz target, the binary for `CPython` also contains shared libraries necessary for the fuzz target.

There is also a binary `experiment_binaries/sqlite3_cov.tar.zst` which is used in RQ4 to count the number of test cases that hit each source file of `SQLite`.

### Baseline data

**Grammars.** `misc/antlr4_isla_grammars.tar.zst` contains the ANTLR4 and ISLa grammars of the seven benchmarks (`librsvg` uses the same grammar as `libxml2`, see Section 6.3). `misc/glade_grammars_and_ground_truths.tar.zst` contains the grammars mined by GLADE, and the grount truth test cases used by GLADE to mine the grammars.

**ISLearn semantic constraints.** `misc/islearn_constraints.tar.zst` contains the semantic constraints learned by ISLearn. `islearn_ground_truth.tar.zst` contains the ground truth test cases and the oracle binaries (that decides whether a test case satisfy the semantic constraints) used by ISLearn to learn the constraints.

**Oracle binaries used by GLADE.** `misc/glade_oracle.tar.zst` contains the oracle binaries (that decides whether a test case is grammatically correct) used by GLADE to mine the grammars.

**Fuzzers synthesized by ELFuzz and its variants.** The `synthesized_fuzzers` directory contains the fuzzers synthesized by ELFuzz and its four variants, viz., ELFuzz-noFS, ELFuzz-noSP, ELFuzz-noCP, and ELFuzz-noIN.

**Time cost of synthesis.** The `timecost` directory contains the manually recorded (using the `time` command) time cost for ELFuzz, ISLearn, and GLADE to synthesize the fuzzers/semantic constraints/grammars.

**Seed test cases produced by each fuzzer.** The `rq1/seeds` directory contains the seed test cases produced by each fuzzer, where `raw` contains the original seed corpora, and `cmined_with_controled_bytes` contains the corpora that have been minimized by `cmin` and prepended random bytes required by some of the fuzz target to select the functionalities under test.

**WARNING.** The corpora in the `raw` directory are super large. You don't want to decompress them unless with 100GiB disk space, and the decompressing can take several hours.

### RQ1 results

`rq1/results` contains the results for RQ1. `afl_cov_exp.tar.zst` contains the raw results (i.e., the AFL++ output directories) of the mutation-based fuzzing experiments in RQ1. `rq1_sum_<rep_n>.xlsx` contains the coverage trends of experiments in each of the 10 repetitions. `rq1_sum.xslx` is the mean coverage across all repetitions. `rq1_std.xlsx` is the standard deviation of the coverage across all repetitions. `seed_cov.xlsx` is the coverage of the seed test cases.

### RQ2 results

The `misc/fr_injected` directory contains the fuzz targets used in RQ2 with bugs injected by FixReverter, each for the three benchmarks `CPython` (the `cpython3` directory), `libxml2`, and `SQLite` (the `sqlite3` directory).

`rq2/results` contains the results for RQ2. `afl_bug_exp.tar.zst` contains the raw results of the bug-injection experiments. `triage.tar.zst` contains the triage results for the crashes found by the experiments. `rq2_count_bug_<rep_n>.xlsx` are the number of bugs found in each repetition of the bug-injection experiments. `rq2_count_bug.xlsx` is the mean number of bugs found across all repetitions. `rq2_std.xlsx` is the standard deviation of the number of bugs found across all repetitions. `rq2_bug_count_10_min_<rep_n>` are the data for Table 6 in each repetition, and `rq2_time_to_trigger` contains the mean values, which is the final results presented in Table 6. `unique_<benchmark>_<fuzzer>.txt` contains the IDs of the unique bugs found by each fuzzer in each benchmark (presented in Figure 10). `failure_<benchmark>.txt` contains the failure cases on each benchmark. `real_world.tar.zst` contains the results of the real-world experiment on `cvc5`, wherein `cvc5/fuzz` contains the AFL++ output directories of the 30 fuzzing processes. There some by-products in the tarball caused by file-writing SMT-LIB2 commands. The triage of the real-world experiment is done manually, so there is no triage data for it. The bugs found by the real-world experiment are in the `cvc5_bugs` directory.

### RQ3 results

The results for RQ3 are in the `rq3/seeds`, `rq3/eval_results`, `rq3_results`, and `evolution_record` directories. `rq3/seeds` contains the seed test cases (the raw copora and copora minimized and prepended with random bytes) produced by ELFuzz-noFS within 10min. `rq3/eval_results` contains the raw outputs (including the seed test cases and the recorded coverage) of ELFuzz-noSP, ELFuzz-noCP, and ELFuzz-noIN. We separate ELFuzz-noFS from other variants and only record the seed test cases it produced without coverage records since when we conduct this experiment, we didn't record the coverage due to ignorance. However, we can still count the coverage for Figure 11 from only the seed test cases. `evolution_record` contains the information of the evolution process (including all 50 evolution iterations) of ELFuzz and the four variants. We accordingly draw Figure 12. The data for Figure 11 are summarized in `rq3_results/rq3_ablation.xlsx`, and the data for Figure 12 are summarized in `rq3_results/rq3_evolve_cov.xlsx`.

### RQ4 results

`rq4/sqlite3_dissection.tar.zst` contains the results of the SQLite3 fuzzer dissection experiment in RQ4, wherein `sampled_test_case` records the IDs of the sampled test cases, and `hit_num.json` records the number of test cases that hit each source file of `SQLite`. `rq4/cvc5_zest.tar.zst` contains the results of the Zest adaptation on the `cvc5` fuzzer experiments in RQ4, including the adapted fuzzer and the 10 test cases for correctness validation.
