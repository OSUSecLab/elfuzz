# ELFuzz

[![Artifact Badge](https://img.shields.io/badge/Artifacts_DOI-10.6084%2Fm9.figshare.29177162-green)](https://doi.org/10.6084/m9.figshare.29177162)

This repository contains the code and experiment data of the paper "ELFuzz: Efficient Input Generation via LLM-driven Synthesis Over Fuzzer Space."

## Experiment data

The experiment data is published on [Figshare](https://doi.org/10.6084/m9.figshare.29177162).

## Replication package

The code and environment to replicate the experiments are published as a Docker image. Run the following command to pull it:

```bash
docker pull ghcr.io/cychen2021/elfuzz:25.06.0   
```

Instead, if you download the Docker image as a tarball from Figshare, you can import it using the following commands:

```bash
zstd -d "elfuzz_docker_<timetag>.tar.zst"
docker load --input "elfuzz_docker_<timetag>.tar"
```

After pulling/importing the image, run the following command to start the container:

```bash
docker run -it ghcr.io/cychen2021/elfuzz:25.06.0
```

This will enter a shell into the container. Then, following the instructions in `/elfuzz/README.md` (which is a symlink to [docker_readme.md](docker_readme.md) in this repository) to replicate the experiments.

The Docker image has only been tested on X86-64 machines.

## How to build the Docker image

Before building the Docker image, you should `cd` to the root of the ELFuzz source code and put `elfuzz_baselines.tar.zst` into `tmp/`.

The Docker image is built by the following command:

```bash
docker build -t ghcr.io/cychen2021/elfuzz:25.06.0 -f .devcontainer/Dockerfile --target publish .
```

## Source code layout

TODO

## Maintenance statement

I tried my best to preserve the environment in the Docker image, keeping the replication package usable for as long as possible. However, there may be some aspects that I have not considered. If you encounter any issues that prevent you from using the package, please open an issue or launch a pull request.
