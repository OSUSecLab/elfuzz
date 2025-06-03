# ELFuzz

This repository contains the code and experiment data of the paper "ELFuzz: Efficient Input Generation via LLM-driven Synthesis Over Fuzzer Space."

## Experiment Data

The experiment data is published on [Figshare](https://doi.org/10.6084/m9.figshare.29177162).

## Replication Package

The code and environment to replicate the experiments is published as a Docker image. Run the following command to pull it:

```bash
docker pull ghcr.io/cychen2021/elfuzz:25.05.0
```

Instead, if you download the Docker image as a tarball from Figshare, you can import it using the following commands:

```bash
zstd -d "elfuzz_docker_<timetag>.tar.zst"
docker load --input "elfuzz_docker_<timetag>.tar"
```

After pulling/importing the image, run the following command to start the container:

```bash
docker run -it ghcr.io/cychen2021/elfuzz:25.05.0
```

This will enter a shell into the container. Then, following the instructions in `/elfuzz/README.md` (which is a symlink to [docker_readme.md](docker_readme.md) in this repository) to replicate the experiments.

The Docker image has only been tested on X86-64 machines.

## How the Docker Image in the Replication Package is Built

Before building the Docker image, you should `cd` to the root of the ELFuzz source code and put `elfuzz_baselines.tar.zst` into `tmp/`.

The Docker image is built by the following command:

```bash
docker build --build-arg -t ghcr.io/cychen2021/elfuzz:25.05.0 -f .devcontainer/Dockerfile --target publish .
```

## Maintainence Statement

I tried my best to persist the environment in the Docker image to keep the replication package usable as long as possible. However, there may be some aspects that I have not considered. If you find any issues that prevent you from using the package, welcome to open an issue or pull request.
