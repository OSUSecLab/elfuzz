from common import PROJECT_ROOT
import os
import tempfile
import subprocess
import pandas as pd
import click
import sys
import itertools

ANALYSIS_ROOT = os.path.join(PROJECT_ROOT, "analysis", "rq1", "results")

BINARY_ROOT = os.path.join(PROJECT_ROOT, "evaluation", 'binary')
WORKDIR_ROOT = os.path.join(PROJECT_ROOT, "evaluation", 'workdir')

BINARIES = {
    "libxml2": os.path.join(BINARY_ROOT, "libxml2", "xml"),
    "re2": os.path.join(BINARY_ROOT, "re2", "fuzzer"),
    "cpython3": os.path.join(WORKDIR_ROOT, "cpython3", "fuzzer"),
    "cvc5": os.path.join(WORKDIR_ROOT, "cvc5", "cvc5"),
    "sqlite3": os.path.join(BINARY_ROOT, "sqlite3", "ossfuzz"),
    "librsvg": os.path.join(BINARY_ROOT, "librsvg", "render_document_patched"),
    "jsoncpp": os.path.join(BINARY_ROOT, "jsoncpp", "jsoncpp_fuzzer")
}

FUZZERS = {
    "elfuzz": "elm",
    "grmr": "grmr",
    "isla": "isla",
    "islearn": "islearn",
    "glade": "glade",
}

ENV = {
    "libxml2": {},
    "re2": {},
    "sqlite3": {},
    "cpython3": {
        "AFL_MAP_SIZE": "2097152"
    },
    "cvc5": {
        "AFL_MAP_SIZE": "2097152",
        "LD_LIBRARY_PATH": os.path.join(WORKDIR_ROOT, "cvc5")
    },
    "librsvg": {
        "AFL_MAP_SIZE": "2097152",
        "AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES": "1",
        "AFL_SKIP_CPUFREQ": "1"
    },
    "jsoncpp": {}
}

BENCHMARKS = [
    "libxml2",
    "re2",
    "cpython3",
    "cvc5",
    "sqlite3",
    "librsvg",
    "jsoncpp"
]

def prepare(fuzzer, benchmark):
    match fuzzer:
        case "elfuzz":
            act_name = "elm"
        case "elfuzz_nofs":
            act_name = "elmalt"
        case "isla":
            act_name = "isla"
        case "islearn":
            act_name = "islearn"
        case "grmr":
            act_name = "grmr"
        case "glade":
            act_name = "elm"
        case "elfuzz_nocp":
            act_name = "elmnocomp"
        case "elfuzz_noin":
            act_name = "elmnoinf"
        case "elfuzz_nosp":
            act_name = "elmnospl"
        case _:
            raise ValueError(f"Unknown fuzzer: {fuzzer}")
    PREPARE_SCRIPT = os.path.join(PROJECT_ROOT, "evaluation", "workdir", "prepare.py")
    cmd = [
        "python", PREPARE_SCRIPT, "-f",
        "-z", act_name,
        benchmark
    ]
    subprocess.run(cmd, check=True)

def run_afl_showmap(input_dir, output_dir, binary, env) -> tuple[str, int]:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    cmd = [
        "/usr/bin/afl-showmap",
        "-i", input_dir,
        "-C",
        "-o", os.path.join(output_dir, "cov"),
        "-t", "5000",
        "--",
        binary, "@@"
    ]

    try:
        ret = subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert ret.returncode == 0
    except Exception as e:
        print(f'Error: {" ".join(cmd)}\n{ret.returncode=}')
        sys.exit(1)

    with open(os.path.join(output_dir, 'cov'), 'r') as cov_f:
        cov_set = set([l.strip().split(':')[0] for l in cov_f.readlines() if l.strip()])
        cov_str = '\n'.join(cov_set)
        count = len(cov_set)
    return cov_str, count

def run_afl_for_librsvg_showmap(input_dir, output_dir, binary, env):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    cmd = [
        "cargo", "afl", "showmap",
        "-i", input_dir,
        "-C",
        "-o", os.path.join(output_dir, "cov"),
        "-t", "5000",
        "--",
        binary,
    ]
    for key, value in env.items():
        os.environ[key] = value
    retcode = os.system(" ".join(cmd) + " > /dev/null 2>&1")
    if retcode != 0:
        print(f'Error: {" ".join(cmd)}')
        sys.exit(1)
    with open(os.path.join(output_dir, "cov"), "r") as cov_f:
        cov_set = set([l.strip().split(":")[0] for l in cov_f.readlines() if l.strip()])
        count = len(cov_set)
        cov_str = "\n".join(cov_set)
    return cov_str, count

def inside_tarball_path(fuzzer, benchmark):
    match fuzzer:
        case "elfuzz":
            dir_suffix = ""
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
    gen_info_dir = os.path.join(PROJECT_ROOT, "extradata", "rq3", "geninfo")
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
        gen_info_dir, f"{benchmark}{info_tarball_suffix}.tar.zst"
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
    seed_dir = os.path.join(PROJECT_ROOT, "extradata", "seeds", "cmined_with_control_bytes", benchmark, subname)
    candidates = [
        f for f in os.listdir(seed_dir) if f.endswith(".tar.zst")
    ]
    candidates.sort(key=lambda f: int(f.removesuffix(".tar.zst")), reverse=True)
    assert len(candidates) > 0, f"No seeds found for {benchmark} with fuzzer {fuzzer}"
    seed_tarball = os.path.join(seed_dir, candidates[0])

    prepare(fuzzer, benchmark)
    with tempfile.TemporaryDirectory() as tmpdir:
        os.mkdir(os.path.join(tmpdir, "input"))
        cmd_unpack = [
            "tar", "--zstd", "-xf", seed_tarball, "-C", os.path.join(tmpdir, "input")
        ]
        subprocess.run(cmd_unpack, check=True)
        input_dir = os.path.join(tmpdir, "input", f"{benchmark}_{subname}")
        output_dir = os.path.join(tmpdir, "output")
        os.mkdir(output_dir)

        binary = BINARIES[benchmark]
        env = ENV[benchmark]
        if benchmark == "librsvg":
            _cov_str, count = run_afl_for_librsvg_showmap(
                input_dir, output_dir, binary, env
            )
        else:
            _cov_str, count = run_afl_showmap(input_dir, output_dir, binary, env)
        return count


def rq1_seed_cov_cmd(fuzzer, benchmark):
    info_tarball = info_tarball_path(fuzzer, benchmark)
    if os.path.exists(info_tarball):
        click.echo(f"Using info tarball for {benchmark} with fuzzer {fuzzer}.")
        cov = rq1_seed_cov_cmd_info_tarball(fuzzer, benchmark)
    else:
        click.echo(f"Using afl-showmap for {benchmark} with fuzzer {fuzzer}.")
        cov = rq1_seed_cov_showmap(fuzzer, benchmark)
    seed_cov_file = os.path.join(ANALYSIS_ROOT, "seed_cov.xlsx")
    df = pd.read_excel(seed_cov_file, index_col=0, header=0, sheet_name=benchmark)
    df.loc[0, fuzzer] = cov
    with pd.ExcelWriter(seed_cov_file) as writer:
        df.to_excel(writer, sheet_name=benchmark, index=True, header=True)
    click.echo(f"Updated seed coverage for {benchmark} with fuzzer {fuzzer}: {cov} edges.")

def rq1_afl_update(entries: list[tuple[str, str, int]]) -> None:
    with tempfile.TemporaryDirectory() as tmpdir_raw:
        tmpdir = os.path.join(tmpdir_raw, "afl_cov_exp")
        if not os.path.exists(tmpdir):
            os.makedirs(tmpdir)
        for benchmark, fuzzer, rep in entries:
            untar_dir = os.path.join(tmpdir, str(rep))
            if not os.path.exists(untar_dir):
                os.makedirs(untar_dir)
            cmd_untar = [
                "tar", "--zstd", "-xf",
                os.path.join(PROJECT_ROOT, "extradata", "rq1", "afl_results", f"{benchmark}_{fuzzer}_{rep}.tar.zst"),
                "-C", untar_dir
            ]
            subprocess.run(cmd_untar, check=True)
            click.echo(f"Unpacked results for {benchmark} with fuzzer {fuzzer}, repetition {rep}.")
        all_reps = set()
        for _, _, rep in entries:
            all_reps.add(rep)
        SUM_REP_SCRIPT = os.path.join(PROJECT_ROOT, "analysis", "rq1", "sum_rep.py")
        for rep in all_reps:
            cmd_sum_rep = [
                "python", SUM_REP_SCRIPT,
                tmpdir_raw,
                "update"
            ]
            subprocess.run(cmd_sum_rep, check=True)
            click.echo(f"Summarized results for repetition {rep} updated.")
        SUM_SCRIPT = os.path.join(PROJECT_ROOT, "analysis", "rq1", "sum.py")
        cmd_sum = [
            "python", SUM_SCRIPT, tmpdir_raw, "update"
        ]
        subprocess.run(cmd_sum, check=True)
        click.echo("Summarized results across all repetitions updated.")
        cmd_std = [
            "python", os.path.join(PROJECT_ROOT, "analysis", "rq1", "std.py"), tmpdir, "update"
        ]
        subprocess.run(cmd_std, check=True)
        click.echo("Standard deviation results updated.")
        click.echo("AFL++ analysis completed.")

def rq1_afl_run(fuzzers, benchmarks, repeat: int, time: int, parallel: int, debug: bool=False) -> list[tuple[str, str, int]]:
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

            prepare(fuzzer, benchmark)
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
        EXPERIMENT_SCRIPT = os.path.join(PROJECT_ROOT, "evaluation", "inputgen", "experiment.py")
        cmd = [
            "python", EXPERIMENT_SCRIPT,
            "-t", str(time),
            "-i", input_dir,
            "-o", output_dir + r"/%d/",
            "-j", str(parallel),
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
                    "-C", os.path.join(output_dir, str(rep)), f"{benchmark}_{subname}"
                ]
                subprocess.run(cmd_tar, check=True)
                collected_info.append(result_file)
                retval.append((benchmark, fuzzer, rep))
        NL = "\n"
        click.echo(f"Results collected:{NL}{NL.join(collected_info)}")
    return retval
