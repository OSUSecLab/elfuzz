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

Then, you need to download the large binary files from Figshare into the local repository. Run the following command to do so:

```bash
elfuzz download
```

This may take a while, and after it finishes, you will get all you need to run the experiments.

You can use `elfuzz config` to configure settings such as email notifications.

## Experiments

Currently, the experiments haven't been automated yet. Though, we have include all code and data needed in this replication package. The experiments have to be run manually for now.
