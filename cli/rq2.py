from common import PROJECT_ROOT
import os
import tempfile
import subprocess
import pandas as pd
import click
import sys
import itertools
from rq1 import FUZZERS, prepare
import itertools

BENCHMARKS = ["libxml2", "cpython3", "sqlite3"]

def rq2_triage_command(fuzzers, benchmarks, repeats):
    with tempfile.TemporaryDirectory() as tmpdir:
        afl_result_dir = os.path.join(tmpdir, "afl_results")
        if not os.path.exists(afl_result_dir):
            os.makedirs(afl_result_dir)
        triage_dir = tmpdir
        if not os.path.exists(triage_dir):
            os.makedirs(triage_dir)

        original_afl_tarball = os.path.join(PROJECT_ROOT, "extradata", "rq2", "afl_results", "afl_bug_exp.tar.zst")
        click.echo(f"Unpacking old AFL++ results from {original_afl_tarball} to {afl_result_dir}")
        cmd_unpack = [
            "tar", "--zstd", "-xf", original_afl_tarball, "-C", afl_result_dir
        ]
        subprocess.run(cmd_unpack, check=True)
        afl_result_dir = os.path.join(afl_result_dir, "afl_bug_exp")
        triage_tarball = os.path.join(PROJECT_ROOT, "extradata", "rq2", "afl_results", "triage.tar.zst")
        click.echo(f"Unpacking old triage results from {triage_tarball} to {triage_dir}")
        cmd_unpack = [
            "tar", "--zstd", "-xf", triage_tarball, "-C", triage_dir
        ]
        subprocess.run(cmd_unpack, check=True)
        triage_dir = os.path.join(triage_dir, "triage")

        to_rerun = []
        for rep, benchmark, fuzzer in itertools.product(repeats, benchmarks, fuzzers):
            if fuzzer == "islearn" and benchmark in ["re2", "jsoncpp"]:
                continue
            separate_afl_tarball = os.path.join(PROJECT_ROOT, "extradata", "rq2", "afl_results", f"{benchmark}_{fuzzer}_{rep}.tar.zst")
            if os.path.exists(separate_afl_tarball):
                cmd_unpack = [
                    "tar", "--zstd", "-xf", separate_afl_tarball, "-C", os.path.join(afl_result_dir, str(rep))
                ]
                subprocess.run(cmd_unpack, check=True)
                click.echo(f"Unpacked {separate_afl_tarball} to {afl_result_dir}")
                to_rerun.append((benchmark, FUZZERS[fuzzer], rep))
        prepare_workdir(triage_dir)
        TRIAGE_SCRIPT = os.path.join(PROJECT_ROOT, "evaluation", "fr_adapt", "triage_all.py")
        click.echo(f"Running triage script {TRIAGE_SCRIPT} on {afl_result_dir} with output to {triage_dir}")
        cmd_triage = [
            "python", TRIAGE_SCRIPT,
            "--root", afl_result_dir,
            "-o", triage_dir,
            "--force-rerun", ",".join(f"{b}_{f}_{r}" for b, f, r in to_rerun),
            "-j", "25",
        ]
        subprocess.run(cmd_triage, check=True)
        cmd_tar = ["tar", "--zstd", "-cf", triage_tarball, "-C", tmpdir, "triage"]
        subprocess.run(cmd_tar, check=True)
        click.echo(f"Triage done. Results stored in {triage_tarball}.")

        COUNT_BUG_REP_SCRIPT = os.path.join(PROJECT_ROOT, "analysis", "rq2", "count_bug_rep.py")
        cmd_count_bug_rep = [
            "python", COUNT_BUG_REP_SCRIPT, triage_dir
        ]
        subprocess.run(cmd_count_bug_rep, check=True)

        COUNT_BUG_SCRIPT = os.path.join(PROJECT_ROOT, "analysis", "rq2", "count_bug.py")
        cmd_count_bug = [
            "python", COUNT_BUG_SCRIPT
        ]
        subprocess.run(cmd_count_bug, check=True)

        STD_SCRIPT = os.path.join(PROJECT_ROOT, "analysis", "rq2", "std.py")
        cmd_std = [
            "python", STD_SCRIPT,
        ]
        subprocess.run(cmd_std, check=True)

        UNIQUE_SCRIPT = os.path.join(PROJECT_ROOT, "analysis", "rq2", "unique.py")
        cmd_unique = [
            "python", UNIQUE_SCRIPT, triage_dir
        ]
        subprocess.run(cmd_unique, check=True)

        SUM_UNIQUE_SCRIPT = os.path.join(PROJECT_ROOT, "analysis", "rq2", "sum_unique.py")
        cmd_sum_unique = [
            "python", SUM_UNIQUE_SCRIPT
        ]
        subprocess.run(cmd_sum_unique, check=True)

        _BUG_COUNT_10_MIN_SCRIPT = os.path.join(PROJECT_ROOT, "analysis", "rq2", "bug_count_10_min.py")
        cmd_bug_count_10_min = [
            "python", _BUG_COUNT_10_MIN_SCRIPT, triage_dir
        ]
        subprocess.run(cmd_bug_count_10_min, check=True)

        TIME_TO_TRIGGER_SCRIPT = os.path.join(PROJECT_ROOT, "analysis", "rq2", "time_to_trigger.py")
        cmd_time_to_trigger = [
            "python", TIME_TO_TRIGGER_SCRIPT
        ]
        subprocess.run(cmd_time_to_trigger, check=True)
        click.echo("RQ2 bug injection experiments done, triaged, and analyzed.")

def prepare_workdir(workdir: str | None = None):
    EXPERIMENT_SCRIPT = os.path.join(PROJECT_ROOT, "evaluation", "fr_adapt", "experiment.py")
    cmd_prepare = ["python", EXPERIMENT_SCRIPT, "--prepare",] + (["-w", workdir,] if workdir is not None else [])
    subprocess.run(cmd_prepare, check=True)

def rq2_afl_run(fuzzers, benchmarks, repeat: int, time: int, parallel: int, debug: bool=False) -> list[tuple[str, str, int]]:
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
            if not os.path.exists(input_dir):
                os.makedirs(input_dir)
            cmd_unpack = [
                "tar", "--zstd", "-xf", seed_tarball, "-C", input_dir
            ]
            subprocess.run(cmd_unpack, check=True)
            prepare_workdir(TMP_WORKDIR)
        click.echo("Starting AFL++ campaigns...")
        output_dir = os.path.join(tmpdir, "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        cmd = [
            "python", EXPERIMENT_SCRIPT,
            "-w", TMP_WORKDIR,
            "-t", str(time),
            "-i", input_dir,
            "-o", output_dir + r"/%d/",
            "-j", str(parallel),
            "-R", str(repeat),
            "-e", ",".join([f"{benchmark}_{fuzzer}" for benchmark, fuzzer in to_exclude])
        ]
        subprocess.run(cmd, check=True)
        click.echo("AFL++ campaigns completed.")
        store_dir = os.path.join(PROJECT_ROOT, "extradata", "rq2", "afl_results")
        collected_info = []
        for rep in range(1, 1+repeat):
            for benchmark, fuzzer in included:
                if (benchmark, fuzzer) in to_exclude:
                    continue
                result_file = os.path.join(store_dir, f"{benchmark}_{fuzzer}_{rep}.tar.zst")
                cmd_tar = [
                    "tar", "--zstd", "-cf", result_file,
                    "-C", os.path.join(output_dir, str(rep - 1)), f"{benchmark}_{FUZZERS[fuzzer]}"
                ]
                subprocess.run(cmd_tar, check=True)
                collected_info.append(result_file)
                retval.append((benchmark, fuzzer, rep))
        NL = "\n"
        click.echo(f"Results collected:{NL}{NL.join(collected_info)}")
    return retval


def rq2_real_world_cmd(resume: bool, output: str, time: int):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = os.path.join(tmpdir, "input")
        os.makedirs(input_dir)
        for benchmark, fuzzer in [("cvc5", "elfuzz")]:
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

            prepare(fuzzer, benchmark)
            if not os.path.exists(input_dir):
                os.makedirs(input_dir)
            cmd_unpack = [
                "tar", "--zstd", "-xf", seed_tarball, "-C", input_dir
            ]
            subprocess.run(cmd_unpack, check=True)
        click.echo("Starting AFL++ campaigns...")
        if resume and (not os.path.exists(output) or not os.path.isdir(output) or not os.listdir(output)):
            click.echo(f"Resume mode set bug output directory {output} is empty or does not exist.")
            return
        EXPERIMENT_SCRIPT = os.path.join(PROJECT_ROOT, "evaluation", "fuzzit", "fuzzit.py")
        cmd = [
            "python", EXPERIMENT_SCRIPT,
            "-t", str(time),
            "-i", input_dir,
            "-o", output,
            "-j", "30",
        ] + (["--resume"] if resume else [])
        subprocess.run(cmd, check=True, env=os.environ)
        click.echo("AFL++ campaigns completed.")

