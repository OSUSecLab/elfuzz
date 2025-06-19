from common import PROJECT_ROOT
import os
import tempfile
import subprocess
import pandas as pd
import click
import sys
import itertools
from rq1 import BENCHMARKS, FUZZERS

def rq2_afl_run(fuzzers, benchmarks, repeat: int, debug: bool=False) -> list[tuple[str, str, int]]:
    to_exclude = [("re2", "islearn"), ("jsoncpp", "islearn")]
    included = list(itertools.product(benchmarks, fuzzers))
    for benchmark, (fuzzer, subname) in itertools.product(BENCHMARKS, FUZZERS.items()):
        if (benchmark, fuzzer) not in included:
            to_exclude.append((benchmark, subname))
    retval = []
    if debug:
        click.echo(f"DEBUG: {to_exclude=}")
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = os.path.join(tmpdir, "input")
        os.makedirs(input_dir)
        EXPERIMENT_SCRIPT = os.path.join(PROJECT_ROOT, "evaluation", "fr_adapt", "experiment.py")
        TMP_WORKDIR = os.path.join(tmpdir, "workdir")
        if not os.path.exists(TMP_WORKDIR):
            os.makedirs(TMP_WORKDIR)
        for benchmark, fuzzer in included:
            if (benchmark, FUZZERS[fuzzer]) in to_exclude:
                continue
            click.echo(f"Preparing input for {benchmark} with fuzzer {fuzzer}...")
            match fuzzer:
                case "elfuzz":
                    subname = "elm"
                case "elfuzz_nofs":
                    subname = "alt"
                case _:
                    subname = fuzzer
            seed_dir = os.path.join(PROJECT_ROOT, "extradata", "seeds", "cmined_with_control_bytes", benchmark, subname)
            candidates = [
                f for f in os.listdir(seed_dir) if f.endswith(".tar.zst")
            ]
            candidates.sort(key=lambda f: int(f.removesuffix(".tar.zst")), reverse=True)
            assert len(candidates) > 0, f"No seeds found for {benchmark} with fuzzer {fuzzer}"
            seed_tarball = os.path.join(seed_dir, candidates[0])

            # prepare(fuzzer, benchmark)
            cmd_prepare = [
                "python", EXPERIMENT_SCRIPT, "--prepare", "-w", TMP_WORKDIR,
            ]
            subprocess.run(cmd_prepare, check=True)
            if not os.path.exists(input_dir):
                os.makedirs(input_dir)
            cmd_unpack = [
                "tar", "--zstd", "-xf", seed_tarball, "-C", input_dir
            ]
            subprocess.run(cmd_unpack, check=True)
        click.echo("Starting AFL++ campaigns...")
        output_dir = os.path.join(tmpdir, "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        cmd = [
            "python", EXPERIMENT_SCRIPT,
            "-w", TMP_WORKDIR,
            "-t", "86400",
            "-i", input_dir,
            "-o", output_dir + r"/%d/",
            # "-j", "25",
            "-r", str(repeat),
            "-e", ",".join([f"{benchmark}_{fuzzer}" for benchmark, fuzzer in to_exclude])
        ]
        subprocess.run(cmd, check=True)
        click.echo("AFL++ campaigns completed.")
        store_dir = os.path.join(PROJECT_ROOT, "extradata", "rq1", "afl_results")
        collected_info = []
        for rep in range(1, 1+repeat):
            for benchmark, fuzzer in included:
                if (benchmark, fuzzer) in to_exclude:
                    continue
                result_file = os.path.join(store_dir, f"{benchmark}_{fuzzer}_{rep}.tar.zst")
                cmd_tar = [
                    "tar", "--zstd", "-cf", result_file,
                    "-C", os.path.join(output_dir, str(rep)), f"{benchmark}_{fuzzer}"
                ]
                subprocess.run(cmd_tar, check=True)
                collected_info.append(result_file)
                retval.append((benchmark, fuzzer, rep))
        NL = "\n"
        click.echo(f"Results collected:{NL}{NL.join(collected_info)}")
    return retval
