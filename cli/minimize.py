import os
import sys
import subprocess
import shutil
import tempfile
from common import PROJECT_ROOT
import click
from datetime import datetime

ALL_FUZZERS = [
    "elm",
    "isla",
    "islearn",
    'grmr',
    'glade',
    'alt'
]

ALL_BENCHMARKS = [
    "libxml2",
    "sqlite3",
    "re2",
    "cpython3",
    "jsoncpp",
    "cvc5",
    "librsvg",
]

def process(fuzzers, benchmarks, tmpdir):
    FUZZER_INV_MAPPING = {
        "elm": "elfuzz",
        "glade": "glade",
        "islearn": "islearn",
        "isla": "isla",
        "grmr": "grmr",
        "alt": "elfuzz_nofs"
    }

    exclude = []
    for fuzzer in ALL_FUZZERS:
        for benchmark in ALL_BENCHMARKS:
            if benchmark not in benchmarks or FUZZER_INV_MAPPING[fuzzer] not in fuzzers:
                exclude.append(f"{benchmark}_{fuzzer}")
    prepare_dir = os.path.join(tmpdir, "prepare")
    os.makedirs(prepare_dir, exist_ok=True)
    BATCH_PROCESS_MR = os.path.join(PROJECT_ROOT, "evaluation", "inputgen", "batchprocess_mr.py")
    cmd = [
        "python", BATCH_PROCESS_MR,
        "-i", os.path.join(PROJECT_ROOT, "extradata", "seeds", "raw"),
        "-o", prepare_dir,
        "--more-excludes", ",".join(exclude),
        "--prepare"
    ]
    subprocess.run(cmd, check=True)

    process_dir = os.path.join(tmpdir, "process")
    os.makedirs(process_dir, exist_ok=True)
    cmd = [
        "python", BATCH_PROCESS_MR,
        "-i", prepare_dir,
        "-o", process_dir,
        "--more-excludes", ",".join(exclude)
    ]
    subprocess.run(cmd, check=True)
    click.echo(f"Random bytes prepended.")

def cmin(fuzzers, benchmarks, tmpdir):
    FUZZER_MAPPING = {
        "elfuzz": "elm",
        "glade": "glade",
        "islearn": "islearn",
        "isla": "isla",
        "grmr": "grmr",
    }

    exclude = []
    for fuzzer in ALL_FUZZERS:
        for benchmark in ALL_BENCHMARKS:
            if benchmark not in benchmarks or fuzzer not in [FUZZER_MAPPING[fuzzer] for fuzzer in fuzzers]:
                exclude.append(f"{benchmark}_{fuzzer}")
    process_dir = os.path.join(tmpdir, "process")
    all_prcs_files = [f.removesuffix(".tar.zst") for f in os.listdir(process_dir) if f.endswith(".tar.zst")]
    intermediate_dir = os.path.join(tmpdir, "intermediate")
    for benchmark in benchmarks:
        for fuzzer_raw in fuzzers:
            fuzzer = FUZZER_MAPPING[fuzzer_raw]
            raw_ori = os.path.join(PROJECT_ROOT, "extradata", "seeds", "raw")
            if f"{benchmark}_{fuzzer}" in ["re2_islearn", "jsoncpp_islearn"]:
                continue
            candidates = [f for f in os.listdir(os.path.join(raw_ori, benchmark, fuzzer)) if f.endswith(".tar.zst")]
            candidates.sort(key=lambda f: int(f.removesuffix(".tar.zst")), reverse=True)
            target_dir = os.path.join(intermediate_dir, "raw_seeds", benchmark, fuzzer)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            shutil.copy(os.path.join(raw_ori, benchmark, fuzzer, candidates[0]),
                        os.path.join(target_dir, "100121.tar.zst"))
            if f"{benchmark}_{fuzzer}" in all_prcs_files:
                prcs_dir = os.path.join(intermediate_dir, "prcs", benchmark, fuzzer)
                if not os.path.exists(prcs_dir):
                    os.makedirs(prcs_dir, exist_ok=True)
                shutil.copy(os.path.join(process_dir, f"{benchmark}_{fuzzer}.tar.zst"),
                            os.path.join(prcs_dir, "100121.tar.zst"))
    cmin_out_dir = os.path.join(tmpdir, "cmin_out")
    BATCH_CMIN_MR = os.path.join(PROJECT_ROOT, "evaluation", "inputgen", "batchcmin_mr.py")
    BATCH_SIZE = 3000
    # We fix the iterations to 10 because 1) the cmin process typically needs multiple runs
    #  and 2) the number of the runs is definitely less than 10 in our experiments.
    
    
    START_FROM = 1
    END_AT = 10
    click.echo(f"Running first cmin iteration. There will be {END_AT} iterations in total.")
    if not os.path.exists(cmin_out_dir):
        os.makedirs(cmin_out_dir, exist_ok=True)
    cmd_first = [
        "python", BATCH_CMIN_MR, "--shuffle",
        "-b", str(BATCH_SIZE),
        "--id", "100121",
        "-i", intermediate_dir,
        "-o", cmin_out_dir,
        "--more-excludes", ",".join(exclude),
        "--move-instead-of-copy",
        "-1",
        "-it", "1",
    ]
    subprocess.run(cmd_first, check=True)

    for i in range(START_FROM + 1, END_AT):
        click.echo(f"Running cmin iteration {i}. There will be {END_AT} iterations in total.")
        cmd_i = [
            "python", BATCH_CMIN_MR, "--shuffle",
            "-b", str(BATCH_SIZE),
            "-i", os.path.join(cmin_out_dir, str(i - 1)),
            "-o", cmin_out_dir,
            "--more-excludes", ",".join(exclude),
            "--move-instead-of-copy",
            "-it", str(i)
        ]
        subprocess.run(cmd_i, check=True)

    click.echo(f"Running last cmin iteration. There will be {END_AT} iterations in total.")
    cmd_last = [
        "python", BATCH_CMIN_MR, "--shuffle",
        "-b", str(BATCH_SIZE),
        "--id", "100121",
        "-i", os.path.join(cmin_out_dir, str(END_AT - 1)),
        "-o", cmin_out_dir,
        "--more-excludes", ",".join(exclude),
        "--move-instead-of-copy",
        "--last-run",
        "-it", str(END_AT)
    ]
    subprocess.run(cmd_last, check=True)
    collect = []
    for benchmark in benchmarks:
        for fuzzer_raw in fuzzers:
            fuzzer = FUZZER_MAPPING[fuzzer_raw]
            if f"{benchmark}_{fuzzer}" in ["re2_islearn", "jsoncpp_islearn"]:
                continue
            output_dir = os.path.join(PROJECT_ROOT, "extradata", "seeds", "cmined_with_control_bytes", benchmark, fuzzer)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            datetag = datetime.now().strftime("%y%m%d")
            output_file = os.path.join(output_dir, f"{datetag}.tar.zst")
            cmd_tar = [
                'tar', '--zstd', '-cf', output_file, '-C', os.path.join(cmin_out_dir, str(END_AT), "cmin"), f'{benchmark}_{fuzzer}'
            ]
            subprocess.run(cmd_tar, check=True)
            collect.append(output_file)
    NL = "\n"
    click.echo(f"Finish processing. Results collected in {NL.join(collect)}")

def minimize_command(
    all: bool = False,
    fuzzer: str | None = None,
    benchmark: str | None = None,
):
    if not all and (fuzzer is None or benchmark is None):
        raise ValueError("If not all, both fuzzer and benchmark must be specified.")
    if all:
        fuzzers = ALL_FUZZERS
        benchmarks = ALL_BENCHMARKS
    else:
        fuzzers = [fuzzer]
        benchmarks = [benchmark]
    with tempfile.TemporaryDirectory() as tmpdir:
        click.echo(f"Prepending control bytes to the test cases...")
        process(fuzzers, benchmarks, tmpdir)
        click.echo(f"Running cmin on the test cases...")
        cmin(fuzzers, benchmarks, tmpdir)
        click.echo(f"Minimization completed.")
