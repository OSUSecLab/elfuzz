from common import PROJECT_ROOT
from rq1 import BENCHMARKS, rq1_seed_cov_cmd_info_tarball, rq1_seed_cov_showmap, info_tarball_path
import os
import pandas as pd
import tempfile
import subprocess
import shutil

def rq3_input_cov_command(debug: bool):
    ablation_file = os.path.join(PROJECT_ROOT, "analysis", "rq3", "results", "rq3_ablation.xlsx")
    dataframe = pd.read_excel(ablation_file, header=0, index_col=0)
    for benchmark in BENCHMARKS:
        if debug and benchmark == "cvc5":
            continue # It's too slow...
        for fuzzer in ["elfuzz", "elfuzz_nofs", "elfuzz_nocp", "elfuzz_noin", "elfuzz_nosp"]:
            p = info_tarball_path(fuzzer, benchmark)
            if not os.path.exists(p):
                print(f"Info tarball {p} not found. Use `rq1_seed_cov_cmd` to generate it.")
                cov = rq1_seed_cov_showmap(fuzzer, benchmark)
            else:
                print(f"Using existing info tarball {p}.")
                cov = rq1_seed_cov_cmd_info_tarball(fuzzer, benchmark)
            dataframe.loc[benchmark, fuzzer] = cov
    with pd.ExcelWriter(ablation_file) as writer:
        dataframe.to_excel(writer)

def rq3_evolve_trend_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        for benchmark in BENCHMARKS:
            for alias, fuzzer in [
                ("elm", "elfuzz"),
                ("nocomp", "elfuzz_noCompletion"),
                ("noinf", "elfuzz_noInfilling"),
                ("nospl", "elfuzz_noSpl"),
                ("alt", "elfuzz_noFS")
            ]:
                copy_to = os.path.join(tmpdir, alias, benchmark)
                if not os.path.exists(copy_to):
                    os.makedirs(copy_to)
                tarball_path = os.path.join(PROJECT_ROOT, "extradata", "evolution_record", fuzzer)
                candidates = [f for f in os.listdir(tarball_path) if f.endswith(".tar.xz") and benchmark in f]
                assert len(candidates) == 1, f"Expected exactly one tarball for {benchmark} in {tarball_path}, found: {candidates}"
                tarball = os.path.join(tarball_path, candidates[0])
                with tempfile.TemporaryDirectory() as tmpdir1:
                    cmd_unpack = [
                        "tar", "-xf", tarball, "-C", tmpdir1
                    ]
                    subprocess.run(cmd_unpack, check=True)
                    components = os.listdir(tmpdir1)
                    if len(components) == 1 and components[0] == "preset":
                        copy_from = os.path.join(tmpdir1, "preset", benchmark)
                    elif len(components) == 1 and components[0] == benchmark:
                        copy_from = os.path.join(tmpdir1, benchmark)
                    else:
                        copy_from = tmpdir1
                    for f in os.listdir(copy_from):
                        # print(f"Moving {f} from {copy_from} to {copy_to}")
                        p = os.path.join(copy_from, f)
                        shutil.move(p, copy_to)
        COLLECT_EVOLVE_COV_SCRIPT = os.path.join(PROJECT_ROOT, "analysis", "rq3", "collect_evolve_cov.py")
        cmd = [
            "python", COLLECT_EVOLVE_COV_SCRIPT, tmpdir
        ]
        subprocess.run(cmd, check=True)