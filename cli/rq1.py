from common import PROJECT_ROOT
import os
import tempfile
import subprocess
import pandas as pd
import click

ANALYSIS_ROOT = os.path.join(PROJECT_ROOT, "analysis", "rq1", "results")

def inside_tarball_path(fuzzer, benchmark):
    match fuzzer:
        case "elfuzz":
            dir_suffix = ""
            info_tarball_suffix = "_elm"
        case "elfuzz_nofs":
            dir_suffix = "_alt"
        case "elfuzz_nocp":
            dir_suffix = "_nocomp"
        case "elfuzz_noin":
            dir_suffix = "_noinf"
        case "elfuzz_nosp":
            dir_suffix = "_nospl"
        case "grmr":
            dir_suffix = "_grammarinator"
        case "isla":
            dir_suffix = "_isla"
        case "islearn":
            dir_suffix = "_islearn"
    return f"{benchmark}{dir_suffix}"

def info_tarball_path(fuzzer, benchmark):
    gen_info_dir = os.path.join(PROJECT_ROOT, "evaluation", "inputgen", "produce_info")
    info_tarball_suffix = ""
    match fuzzer:
        case "elfuzz":
            info_tarball_suffix = "_elm"
        case "elfuzz_nofs":
            info_tarball_suffix = "_alt"
        case "elfuzz_nocp":
            info_tarball_suffix = "_nocomp"
        case "elfuzz_noin":
            info_tarball_suffix = "_noinf"
        case "elfuzz_nosp":
            info_tarball_suffix = "_nospl"
        case "grmr":
            info_tarball_suffix = "_grammarinator"
        case "isla":
            info_tarball_suffix = "_isla"
        case "islearn":
            info_tarball_suffix = "_islearn"
    info_tarball = os.path.join(
        gen_info_dir, f"{benchmark}_{fuzzer}{info_tarball_suffix}.tar.zst"
    )
    return info_tarball

def rq1_seed_cov_cmd_info_tarball(fuzzer, benchmark) -> int:
    info_tarball = info_tarball_path(fuzzer, benchmark)
    inside_dir = inside_tarball_path(fuzzer, benchmark)
    cov_sum = f"{inside_dir}/sum.cov"
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "tar", "--zstd", "-xf", info_tarball, "-C", tmpdir, cov_sum
        ]
        subprocess.run(cmd, check=True)
        with open(os.path.join(tmpdir, cov_sum), "r") as f:
            lines = f.readlines()
            return len(lines)

def rq1_seed_cov_showmap(fuzzer, benchmark) -> int:
    match fuzzer:
        case "elfuzz":
            subname = "elm"
        case "elfuzz_nofs":
            subname = "alt"
        case _:
            subname = fuzzer
    seed_dir = os.path.join("extradata", "seeds", "cmined_with_control_bytes", benchmark, subname)
    candidates = [
        f for f in os.listdir(seed_dir) if f.endswith(".tar.zst")
    ]
    candidates.sort(key=lambda f: int(f.removesuffix(".tar.zst")), reverse=True)
    assert len(candidates) > 0, f"No seeds found for {benchmark} with fuzzer {fuzzer}"
    seed_tarball = os.path.join(seed_dir, candidates[0])
    cmd = []
    ...

def rq1_seed_cov_cmd(fuzzer, benchmark):
    info_tarball = info_tarball_path(fuzzer, benchmark)
    if os.path.exists(info_tarball):
        cov = rq1_seed_cov_cmd_info_tarball(fuzzer, benchmark)
    else:
        cov = rq1_seed_cov_showmap(fuzzer, benchmark)
    seed_cov_file = os.path.join(ANALYSIS_ROOT, "seed_cov.xlsx")
    df = pd.read_excel(seed_cov_file, index_col=0, header=0, sheet_name=benchmark)
    df.loc[fuzzer, 0] = cov
    with pd.ExcelWriter(seed_cov_file) as writer:
        df.to_excel(writer, sheet_name=benchmark, index=True, header=True)
    click.echo(f"Updated seed coverage for {benchmark} with fuzzer {fuzzer}: {cov} edges.")
