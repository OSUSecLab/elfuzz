# How to Use This ELFuzz Docker Image

[![Read on GitHub](https://img.shields.io/badge/Read%20on%20GitHub-cychen2021%2Felfuzz%3Adocker__readme.md-yellow)](https://github.com/cychen2021/elfuzz/blob/main/docker_readme.md)

This Docker image contains source code, data, and utilities to reproduce the experiments presented in the paper "ELFuzz: Efficient Input Generation via LLM-driven Synthesis Over Fuzzer Space."

## Source location

In the following instructions, you will work in the directory `/elfuzz/`. However, the actual source location is `/home/appuser/elmfuzz/`. In this document, all relative paths are relative to `/home/appuser/elmfuzz/`.

This file is a symlink to `/home/appuser/elmfuzz/docker_readme.md`. `docs/` is a symlink to `/home/appuser/elmfuzz/docs/`. Later experiments will create some files and directories in `/elfuzz/` and they are also symlinks to the actual source location. You can use `realpath` to check where they point to.

## Launching and setting up the container

The experiments require [sibling containers](https://stackoverflow.com/questions/39151188/is-there-a-way-to-start-a-sibling-docker-container-mounting-volumes-from-the-hos). You'll need to run the following command to enable them:

```bash
elfuzz setup
```

You'll need to restart this container manually after the command finishes to make the changes take effect. First, inside the container, run the following command to exit:

```bash
exit
```

Then, run the following command to restart the container (suppose that you followed the instructions in the `README.md` file in the source code tarball and named the container `elfuzz`):

```bash
docker start -ai elfuzz
```

Then, you need to download the large binary files from Figshare into the local repository. Run the following command to do so:

```bash
elfuzz download
```

This may take a while, and after it finishes, you will get all you need to run the experiments.

## Configuring Hugging Face token

The experiments require pulling models from Hugging Face. You need to set up your [Hugging Face token](https://huggingface.co/docs/hub/en/security-tokens) via the following command:

```bash
elfuzz config --set tgi.huggingface_token "<your_token>"
```

Besides, you can optionally use `elfuzz config` to configure settings such as email notifications.

## Experiments

The following sections describe how to reproduce the experiments presented in the paper. Note that we include all intermediate results acquired in our previous experiments, so you can skip any steps that you don't have time or resources to run.

### Synthesizing fuzzers by ELFuzz and its four variants

Run the following command to synthesize fuzzers using ELFuzz or one of its variants:

```bash
elfuzz synth -T "fuzzer.(elfuzz|elfuzz_nofs|elfuzz_nocp|elfuzz_noin|elfuzz_nosp)" "<benchmark>"
```

where `<benchmark>` can be chosen from the seven benchmarks used in the paper, viz.,

- `jsoncpp`
- `libxml2`
- `re2`
- `cpython3` (CPython in the paper)
- `sqlite3` (SQLite in the paper)
- `cvc5`
- `librsvg`

The evolution iterations will be recorded in folders named `preset/<benchmark>/gen<it_n>/`, where `<it_n>` can be 0 to 50. The `*.py` files in `preset/<benchmark>/gen50/seeds/` are the final result of the evolution.

NOTE: You should manually record the start and end time of each synthesis run to calculate the time cost.

The evolved fuzzers will be in the following tarballs:

- `evaluation/elmfuzz/<benchmark>_<timetag>.tar.xz` for ELFuzz
- `evaluation/alt_elmfuzz/<benchmark>_<timetag>.tar.xz` for ELFuzz-noFS
- `evaluation/nocomp_fuzzers/<benchmark>_<timetag>.tar.xz` for ELFuzz-noCP
- `evaluation/noinf_fuzzers/<benchmark>_<timetag>.tar.xz` for ELFuzz-noIN
- `evaluation/nospl_fuzzers/<benchmark>_<timetag>.tar.xz` for ELFuzz-noSP

The evolution iterations will be in the following tarballs:

- `extradata/evolution_record/elfuzz` for ELFuzz
- `extradata/evolution_record/elfuzz_noFS` for ELFuzz-noFS
- `extradata/evolution_record/elfuzz_noCompletion` for ELFuzz-noCP
- `extradata/evolution_record/elfuzz_noInfilling` for ELFuzz-noIN
- `extradata/evolution_record/elfuzz_noSpl` for ELFuzz-noSP

### Mining grammars by GLADE

Run the following command to mine grammars using GLADE:

```bash
elfuzz synth -T grammar.glade "<benchmark>"
```

The grammar will be put in `evaluation/gramgen/<benchmark>/<timestamp>.gram`.

### Mining semantic constraints by ISLearn

Run the following command to mine semantic constraints using ISLearn:

```bash
elfuzz synth -T semantics.islearn "<benchmark>"
```

The semantic constraints will be put in `extradata/islearn_constraints/<benchmark>.json`. By default, the command will randomly choose one semantic constraint from ones with the best recall and precision if there are multiple candidates and put it into the corresponding `*.isla` file in a file named `evaluation/islearn_adapt/selected/<benchmark>_*.isla` to be used by ISLa and ISLearn in later experiments. You can use the `--no-select` flag to disable this. If so, you will need to manually select one semantic constraint and put it into that file.

### Producing and minimizing seed test cases

#### WARNINGS

- This step will produce enormous amounts of test cases, especially when using ELFuzz or its variants. There will be data of more than 50 GiB consisting of small files, so even deleting them will take a long time.
- The generation process typically takes a long time to finish. We produce the test cases in batches and use the total time of the batches as the generation time. For example, if we generate three batches, which take 10 min, 15 min, and 20 min respectively, the generation time is 45 min. Between batches, we use `afl-showmap` to incrementally compute the coverage of the test cases, and that is why the overall time (typically one day for ELFuzz) is much longer than the generation time.
- Due to the above reasons, I suggest you to just skip this step and start the experiments from seed test cases we produced ahead of time if you don't have enough time or resources to run it.

#### Producing test cases

After synthesizing all the fuzzers/grammars/semantic constraints, you can produce seed test cases using the following command:

```bash
elfuzz produce -T "(elfuzz|elfuzz_nofs|elfuzz_nocp|elfuzz_noin|elfuzz_nosp|glade|isla|islearn|grmr)" "<benchmark>"
```

The test cases will be stored in subdirectories of `extradata/seeds/raw/<benchmark>/`:

- `elm/` for ELFuzz
- `elmalt/` for ELFuzz-noFS
- `elmnocomp/`: for ELFuzz-noCP
- `elmnoinf/`: for ELFuzz-noIN
- `elmnospl/`: for ELFuzz-noSP
- `grmr/` for Grmr
- `isla/` for ISLa
- `islearn/` for ISLearn
- `glade/` for GLADE

#### Minimizing test cases

The generated test cases are enormous. Besides, some fuzz targets require random bytes prepended to control the features under test. Run the following command to minimize the test cases use `afl-cmin` and prepend the random bytes:

```bash
elfuzz minimize -T "(elfuzz|glade|isla|islearn|grmr)" "<benchmark>"
```

Note that we don't support minimizing test cases generated by the variants of ELFuzz, as this is unnecessary. Evaluation in our paper didn't feed the test cases generated by these variants to AFL++ for mutation-based fuzzing. The minimized and bytes-prepended test cases will be stored in tarballs in `extradata/seeds/cmined_with_control_bytes/`. The name of each tarball will be `<yymmdd>.tar.zst`. Tarballs with the newest timestamp in the names should be the ones that you have just processed.

### Conducting RQ1 experiments

#### Compute the coverage of the seed test cases

To replicate the results in Figure 7, run the following command:

```bash
elfuzz run rq1.seed_cov -T "(elfuzz|glade|isla|islearn|grmr)" "<benchmark>"
```

The results will be updated to `/elfuzz/analysis/rq1/results/seed_cov.xlsx`. You can use the following command to inspect it:

```bash
pyexcel view /elfuzz/analysis/rq1/results/seed_cov.xlsx
```

or this one for a specific benchmark:

```bash
pyexcel view --sheet-name "<benchmark>" /elfuzz/analysis/rq1/results/seed_cov.xlsx
```

#### Running the AFL++ fuzzing campaigns

To replicate the results in Figure 8, run the following command:

```bash
elfuzz run rq1.afl --fuzzers "elfuzz,grmr,isla,islearn,glade" --repeat 10 "jsoncpp,libxml2,re2,cpython3,sqlite3,cvc5,librsvg"
```

This command will run the AFL++ fuzzing campaigns for the fuzzers and benchmarks listed 10 times. The campaigns will be run in batches each running 25 campaigns in parallel. The raw AFL++ outputs will be put in `extradata/rq1/afl_results/<benchmark>_<fuzzer>_<rep_n>.tar.zst`. The analysis results will be updated in `/elfuzz/analysis/rq1/results/rq1_(std|sum|sum_<rep_n>).xlsx`.

### Conducting RQ2 experiments

#### Running the AFL++ fuzzing campaigns on the bug-injected benchmarks

To reproduce the results in Figure 9, Figure 10, and Table 6, we need to run the AFL++ fuzzing campaigns on the bug-injected benchmarks via the following command:

```bash
elfuzz run rq2.afl --fuzzers "elfuzz,grmr,isla,islearn,glade" --repeat 10 "libxml2,cpython3,sqlite3"
```

The output of AFL++ will be stored in tarballs in `extradata/rq2/afl_results/<benchmark>_<fuzzer>_<rep_n>.tar.zst`.

#### Triaging and analyzing the results

Then, run the following command to triage and analyze the results:

```bash
elfuzz run rq2.triage
```

The outputs of the analysis will be in `/elfuzz/analysis/rq2/results/`:

- `rq2_count_bug_<rep_n>.xlsx` are the data for Figure 9 per repetition. `rq2_count_bugs.xlsx` is the averaged data, and `rq2_std.xlsx` is the standard deviations.
- `rq2_bug_count_10_min_<rep_n>.xlsx` are the data for Table 6 per repetition. `rq2_time_to_trigger.xlsx` is the averaged data presented in the table.
- `unique_<benchmark>_<fuzzer>.txt` (ELFuzz represented as `elm`) contains the unique bugs triggered by each fuzzer on each benchmark. `unique.xlsx` is the aggregated value of each fuzzer presented in Figure 10.

#### Running the real-world experiment on cvc5.

Use the following command to run the real-world bug-finding experiment on cvc5 for 14 days:

```bash
elfuzz run rq2.real_world --time 1209600
```

AFL++ will output to `/home/appuser/cvc5_realworld`. You can checkpoint the directory into a tarball in `/elfuzz/cvc5_realworld/` by running the following command:

```bash
elfuzz run rq2.real_world --checkpoint
```

### Conducting RQ3 experiments

### Conducting RQ4 experiments

## Result analysis and visualization

## Copying out the results

After all the above processes, running the following command in the host shell to copy out all the results from the container:

```bash
docker cp --follow-link "elfuzz:/elfuzz/*" "<dest_dir>/"
```
