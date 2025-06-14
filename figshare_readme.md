# Replication Package of ELFuzz

[![Static Badge](https://img.shields.io/badge/GitHub-cychen2021%2Felfuzz-orange)](https://github.com/cychen2021/elfuzz)

## Overview

This Figshare repository contains the replication package for the paper *ELFuzz: Efficient Input Generation via LLM-driven Synthesis Over Fuzzer Space*.

The files are organized as follows:

- `elfuzz_src.tar.zst`: The source code of ELFuzz.
- `elfuzz_data_<timetag>.tar.zst.part<suffix>`: The experiment data.
- `elfuzz_docker_<timetag>.tar.zst.part<suffix>`: The Docker image to replicate the experiments.
- `elfuzz_baselines.tar.zst`: The source code of the baselines used in the experiments.
- `data_metadata.json`: Metadata information about the experiment data tarball.
- `docker_metadata.json`: Metadata information about the Docker image tarball.

You can download the data or Docker image and run the following command to combine the parts into a complete tarball:

```bash
cat "elffuzz_(data|docker)_<timetag>.tar.zst.part*" > "elffuzz_(data|docker)_<timetag>.tar.zst"
```

The source code tarball contains a `README.md` file that describes how to replicate the experiments.

Note that you need to install `zstd` to decompress the tarballs. On Ubuntu, use the following command to install it:

```bash
sudo apt install zstd
```

Then, decompress the tarballs using the following command:

```bash
zstd -d "elfuzz_(src|data|docker)_<timetag>.tar.zst"
```

In the following sections, we will list the important contents of each tarball.

## Contents of the ELFuzz source code tarball

## Contents of the baseline tarball

## Contents of the experiment data tarball

### Benchmark data

**Binaries for mutation-based fuzzing.** Binaries of the benchmarks that is used as fuzz targets in for the mutation-based fuzzing in RQ1 and RQ2 are in the `experiment_binaries` directory. The seven tarballs are for the seven benchmarks respectively: `jsoncpp.tar.zst`, `libxml2.tar.zst`, `re2.tar.zst`, `sqlite3.tar.zst` (for `SQLite`), `cpython3.tar.zst` (for `CPython`), `cvc5.tar.zst`, and `librsvg.tar.zst`.

**Binaries with injected bugs.** Binaries with injected bugs used in RQ2 are in the `misc/fr_injected` directory. `cpython3`, `libxml2`, and `sqlite3` contain the bug-injected binaries for `CPython`, `libxml2`, and `SQLite` respectively. Note that except the fuzz target, the binary for `CPython` also contains shared libraries necessary for the fuzz target.

There is also a binary `experiment_binaries/sqlite3_cov.tar.zst` which is used in RQ4 to count the number of test cases that hit each source file of `SQLite`.

### Baseline data

**Grammars.** `misc/antlr4_isla_grammars.tar.zst` contains the ANTLR4 and ISLa grammars of the seven benchmarks (`librsvg` uses the same grammar as `libxml2`, see Section 6.3). `misc/glade_grammars_and_ground_truths.tar.zst` contains the grammars mined by GLADE, and the grount truth test cases used by GLADE to mine the grammars.

**ISLearn semantic constraints.** `misc/islearn_constraints.tar.zst` contains the semantic constraints learned by ISLearn. `islearn_ground_truth.tar.zst` contains the ground truth test cases and the oracle binaries (that decides whether a test case satisfy the semantic constraints) used by ISLearn to learn the constraints.

**Oracle binaries used by GLADE.** `misc/glade_oracle.tar.zst` contains the oracle binaries (that decides whether a test case is grammatically correct) used by GLADE to mine the grammars.

**Fuzzers synthesized by ELFuzz and its variants.** The `synthesized_fuzzers` directory contains the fuzzers synthesized by ELFuzz and its four variants.

**Time cost of synthesis.** The `timecost` directory contains the manually recorded (using the `time` command) time cost for ELFuzz, ISLearn, and GLADE to synthesize the fuzzers/semantic constraints/grammars.

**Seed test cases produced by each fuzzer.** The `rq1/seeds` directory contains the seed test cases produced by each fuzzer, where `raw` contains the original seed corpora, and `cmined_with_controled_bytes` contains the corpora that have been minimized by `cmin` and prepended random bytes required by some of the fuzz target to select the functionalities under test. Note that the corpus in `raw` are super large. You don't want to decompress them unless with 100GiB disk space.

### RQ1 results

### RQ2 results

### RQ3 results

### RQ4 results
