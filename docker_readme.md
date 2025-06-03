# How to Use This ELFuzz Docker Image

## Source Location

In the following instructions, you will work in the directory `/elfuzz/`. However, the actual source location is `/home/appuser/elmfuzz/`.

This file is a symlink to `/home/appuser/elmfuzz/docker_readme.md`. `docs/` is a symlink to `/home/appuser/elmfuzz/docs/`. Files and directories created in the later experiments are mostly symlinks to files or directories in the actual source location. You can use `realpath` to check where they point to.

## Launching and Setting Up the Container

The experiments require [sibling containers](https://stackoverflow.com/questions/39151188/is-there-a-way-to-start-a-sibling-docker-container-mounting-volumes-from-the-hos). You'll need to run the following command to enable them:

```bash
elfuzz setup
```

You'll need to restart this container manually after the command finishes to make the changes take effect.

Then, you need to download the large binary files from Zenodo into the local repository. Run the following command to do so:

```bash
elfuzz download
```

This may take a while, and after it finishes, you will get all you need to run the experiments.

## Experiments

### Synthesizing Input Generators

After enabling sibling containers and restarting the container, you can start synthesizing input generators by following the instructions below.

### Preparing Baselines
