# How to Use This ELFuzz Docker Image

[![Read on GitHub](https://img.shields.io/badge/Read%20on%20GitHub-cychen2021%2Felfuzz%3Adocker__readme.md-yellow)](https://github.com/cychen2021/elfuzz/blob/main/docker_readme.md)

This Docker image contains source code, data, and utilities to reproduce the experiments presented in the paper "ELFuzz: Efficient Input Generation via LLM-driven Synthesis Over Fuzzer Space."

## Source location

In the following instructions, you will work in the directory `/elfuzz/`. However, the actual source location is `/home/appuser/elmfuzz/`.

This file is a symlink to `/home/appuser/elmfuzz/docker_readme.md`. `docs/` is a symlink to `/home/appuser/elmfuzz/docs/`. Files and directories created in the later experiments are mostly symlinks to files or directories in the actual source location. You can use `realpath` to check where they point to.

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

#### TODOs

- [ ] Currently, the results of multiple runs of the synthesis (no matter whether you run ELFuzz or its variants) will overwrite each other. We have to fix this.

### Mining grammars by GLADE

### Mining semantic constraints by ISLearn

### Producing and minimizing seed test cases

### Conducting RQ1 experiments

### Conducting RQ2 experiments

### Conducting RQ3 experiments

### Conducting RQ4 experiments

## Result analysis and visualization
