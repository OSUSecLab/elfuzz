# ELFuzz: Efficient Input Generation via LLM-driven Synthesis Over Fuzzer Space

This Figshare repository contains the replication package for the paper "ELFuzz: Efficient Input Generation via LLM-driven Synthesis Over Fuzzer Space."

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

Note that you need to install `zstd` to decompress the tarballs.
