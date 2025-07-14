import os
import subprocess
from datetime import datetime
import sys
import shutil
import click
from common import PROJECT_ROOT, CLI_DIR, USER, trim_indent, UID
from datetime import datetime
import tempfile
import json
from typing import Dict
import select

def synthesize_semantics(benchmark, no_select: bool):
    click.echo(f"Preparing environments...")
    cmd_prepare_base = ["sudo", f"ELMFUZZ_RUNDIR=preset/{benchmark}", "python", os.path.join(PROJECT_ROOT, "prepare_fuzzbench.py")]
    match benchmark:
        case "jsoncpp" | "libxml2" | "re2" | "sqlite3":
            pass
        case "cpython3" | "librsvg":
            cmd_prepare_base += ["-d", "/home/appuser/oss-fuzz", "-t", "oss-fuzz"]
        case "cvc5":
            cmd_prepare_base += ["-t", "docker"]
    # env = os.environ.copy() | {"ELMFUZZ_RUNDIR": f"preset/{benchmark}"}
    env = os.environ.copy()
    subprocess.run(" ".join(cmd_prepare_base), check=True, env=env, shell=True,
                   cwd=PROJECT_ROOT, stdout=sys.stdout, stderr=sys.stderr, user=USER)
    cmd_prepare = ["sudo", "python", os.path.join(PROJECT_ROOT, "evaluation", "islearn_adapt", "prepare_islearn.py"), benchmark]
    subprocess.run(" ".join(cmd_prepare), shell=True, check=True, env=env, cwd=PROJECT_ROOT, stdout=sys.stdout, stderr=sys.stderr, user=USER)
    click.echo(f"Mining semantic constraints...")
    stored_dir = os.path.join(PROJECT_ROOT, "extradata", "islearn_constraints")
    if not os.path.exists(stored_dir):
        os.makedirs(stored_dir)
    with tempfile.TemporaryDirectory(prefix="/tmp/host/") as tmpdir:
        cmd_mine = ["sudo", "docker", "run", "--rm", "-v", f"{tmpdir}:/tmp/semantics", f"elmfuzz/{benchmark}_islearn",
                    "conda", "run", "-n", "py310", "/bin/bash", "-c", f"python infer_semantics.py -o /tmp/semantics/{benchmark}.json grammar.bnf"]
        subprocess.run(cmd_mine, check=True, env=os.environ.copy(), cwd=PROJECT_ROOT, stdout=sys.stdout, stderr=sys.stderr)
        existing = [os.path.join(stored_dir, f) for f in os.listdir(stored_dir) if f.endswith(".json") and benchmark in f]
        assert len(existing) <= 1, f"Expected at most one existing semantic constraints file for {benchmark}, found {len(existing)}"
        if existing:
            os.remove(existing[0])
            click.echo(f"Storing semantic constraints for {benchmark}...")
        shutil.copy(os.path.join(tmpdir, f"{benchmark}.json"), os.path.join(stored_dir, f"{benchmark}.json"))
    if not no_select:
        with open(os.path.join(stored_dir, f"{benchmark}.json"), "r") as f:
            constraints: Dict[str, Dict] = json.load(f)
        if not constraints:
            click.echo(f"WARNING: No semantic constraints successfully mined for {benchmark}.")
        else:
            best_constraint = max(constraints.values(), key=lambda x: (x.get("recall", 0), x.get("precision", 0)))
            selected_dir = os.path.join(PROJECT_ROOT, "evaluation", "islearn_adapt", "selected")
            files = [os.path.join(selected_dir, f) for f in os.listdir(selected_dir) if f.endswith(".isla") and benchmark in f]
            assert len(files) == 1, f"Expected exactly one selected semantic constraints file for {benchmark}, found {len(files)}"
            with open(files[0], "w") as f:
                f.write(best_constraint["rule"])
            click.echo("A random best constraint selected")
    click.echo(f"Semantic constraints for {benchmark} synthesized successfully: {os.path.join(stored_dir, f'{benchmark}.json')}")

def synthesize_grammar(benchmark):
    inputs_dir = os.path.join(PROJECT_ROOT, "evaluation", "gramgen", benchmark, "inputs")

    GLADE_DIR = os.path.join("/", "home", USER, "glade")
    target_dir = os.path.join(GLADE_DIR, "inputs")

    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)

    shutil.copytree(inputs_dir, target_dir, dirs_exist_ok=True)
    GLADE_ORACLE_DIR = os.path.join(PROJECT_ROOT, "evaluation", "glade_oracle")

    match benchmark:
        case "xml":
            oracle_cmd = f"{os.path.join(GLADE_ORACLE_DIR, 'xml')} {{/}}"
        case "re2":
            oracle_cmd = f"{os.path.join(GLADE_ORACLE_DIR, 're2_fuzzer')} {{/}}"
        case "sqlite3":
            oracle_cmd = f"{os.path.join(GLADE_ORACLE_DIR, 'sqlite3_parser')} {{/}}"
        case "jsoncpp":
            oracle_cmd = f"{os.path.join(GLADE_ORACLE_DIR, 'jsoncpp_fuzzer')} {{/}}"
        case "cpython3":
            oracle_cmd = f"python {os.path.join(GLADE_ORACLE_DIR, 'pyparser.py')} {{/}}"
        case "librsvg":
            oracle_cmd = f"{os.path.join(GLADE_ORACLE_DIR, 'render_document')}"
        case "cvc5":
            oracle_cmd = f"python {os.path.join(GLADE_ORACLE_DIR, 'cvc5_parser.py')} {{/}}"
        case _:
            raise ValueError(f"Unknown benchmark: {benchmark}")

    learn_cmd = ["./gradlew", "run", f"--args=\"learn -l 0-100 '{oracle_cmd}'\""]
    click.echo(f"Running GLADE to mine grammar for {benchmark} (may needs several hours)...")
    click.echo(f"Command: {' '.join(learn_cmd)}")
    subprocess.run(" ".join(learn_cmd), check=True, env=os.environ.copy() | {"JAVA_HOME": "/home/appuser/.sdkman/candidates/java/current/"},
                   cwd=GLADE_DIR, user=USER, shell=True)
    gram_dir = os.path.join(GLADE_DIR, "evaluation", "gramgen", benchmark)
    if not os.path.exists(gram_dir):
        os.makedirs(gram_dir)
    for file in os.listdir(gram_dir):
        if file.endswith(".gram"):
            os.remove(os.path.join(gram_dir, file))
    gram_file_generated = [file for file in os.listdir(GLADE_DIR) if file.endswith(".gram")]
    assert len(gram_file_generated) > 0, f"Expected at least one grammar file, found 0"
    def parse_time(text: str) -> float:
        from datetime import datetime
        time_str = text.removesuffix(".gram")
        t = datetime.strptime(time_str, "%Y-%m-%d_%H:%M")
        return t.timestamp()
    gram_file_generated.sort(key=parse_time)

    shutil.move(os.path.join(GLADE_DIR, gram_file_generated[0]), os.path.join(gram_dir, gram_file_generated[0]))
    click.echo(f"Grammar for {benchmark} synthesized successfully: {os.path.join(gram_dir, gram_file_generated[0])}.")

def synthesize_fuzzer(target, benchmark, *, tgi_waiting=600, evolution_iterations=50, use_small_model=False):
    match target:
        case "elfuzz":
            env = os.environ.copy() | {
                "SELECTION_STRATEGY": "lattice",
                "ELFUZZ_FORBIDDEN_MUTATORS": ""
            }
        case "elfuzz_nofs":
            env = os.environ.copy() | {
                "SELECTION_STRATEGY": "elites",
                "ELFUZZ_FORBIDDEN_MUTATORS": "",
            }
        case "elfuzz_nocp":
            env = os.environ.copy() | {
                "SELECTION_STRATEGY": "lattice",
                "ELFUZZ_FORBIDDEN_MUTATORS": "complete",
            }
        case "elfuzz_noin":
            env = os.environ.copy() | {
                "SELECTION_STRATEGY": "lattice",
                "ELFUZZ_FORBIDDEN_MUTATORS": "infilling",
            }
        case "elfuzz_nosp":
            env = os.environ.copy() | {
                "SELECTION_STRATEGY": "lattice",
                "ELFUZZ_FORBIDDEN_MUTATORS": "lmsplicing",
            }
        case _:
            raise ValueError(f"Unknown target: {target}")

    cmd_tgi = ["sudo", os.path.join(PROJECT_ROOT, "start_tgi_servers.sh" if not use_small_model else "start_tgi_servers_debug.sh")]
    click.echo(f"Starting the text-gneration-inference server. This may take a while as it has to download the model...")

    try:
        tgi_p = subprocess.Popen(" ".join(cmd_tgi), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                 env=env, cwd=PROJECT_ROOT, user=USER, text=True)
        start = datetime.now()
        print(f"TGI server started at {start}.", flush=True)
        poll_obj = select.poll()
        assert tgi_p.stdout is not None, "TGI server stdout is None."
        poll_obj.register(tgi_p.stdout, select.POLLIN)
        while True:
            if tgi_p.poll() is not None:
                print("TGI server failed to start.", flush=True)
                print("stderr:", flush=True)
                print(tgi_p.stderr.read(), flush=True) # type: ignore
                print("stdout:", flush=True)
                print(tgi_p.stdout.read(), flush=True) # type: ignore
                raise RuntimeError("TGI server failed to start.")
            if (datetime.now() - start).total_seconds() > tgi_waiting:
                break
            if poll_obj.poll(20):
                line = tgi_p.stdout.readline().strip()
                if line:
                    print(line, flush=True)
        click.echo("Text-generation-inference server started.")
    except Exception as e:
        raise e

    try:
        rundir = os.path.join("preset", benchmark)

        if evolution_iterations != 50:
            cmd = ["sudo", "REPROUDCE_MODE=true", f"NUM_GENERATIONS={evolution_iterations}", os.path.join(PROJECT_ROOT, "all_gen.sh"), rundir]
        else:
            cmd = ["sudo", "REPROUDCE_MODE=true", os.path.join(PROJECT_ROOT, "all_gen.sh"), rundir]
        print(f"Running command: {' '.join(cmd)}", flush=True)
        subprocess.run(" ".join(cmd), check=True, shell=True, user=USER, cwd=PROJECT_ROOT, stdout=sys.stdout, stderr=sys.stderr)

        match target:
            case "elfuzz":
                target_cap = "elfuzz"
                fuzzer_dir = os.path.join(PROJECT_ROOT, "evaluation", "elmfuzzers")
            case "elfuzz_nofs":
                target_cap = "elfuzz_noFS"
                fuzzer_dir = os.path.join(PROJECT_ROOT, "evaluation", "alt_elmfuzzers")
            case "elfuzz_nocp":
                target_cap = "elfuzz_noCompletion"
                fuzzer_dir = os.path.join(PROJECT_ROOT, "evaluation", "nocomp_fuzzers")
            case "elfuzz_noin":
                target_cap = "elfuzz_noInfilling"
                fuzzer_dir = os.path.join(PROJECT_ROOT, "evaluation", "noinf_fuzzers")
            case "elfuzz_nosp":
                target_cap = "elfuzz_noSpl"
                fuzzer_dir = os.path.join(PROJECT_ROOT, "evaluation", "nospl_fuzzers")

        evolution_record_dir = os.path.join(PROJECT_ROOT, "extradata", "evolution_record", target_cap)
        if not os.path.exists(evolution_record_dir):
            os.makedirs(evolution_record_dir)
        else:
            for file in os.listdir(evolution_record_dir):
                os.remove(os.path.join(evolution_record_dir, file))
        tar_evolution_cmd = ["tar", "-cJf", os.path.join(evolution_record_dir, "evolution.tar.xz"), rundir]
        subprocess.run(tar_evolution_cmd, check=True, cwd=PROJECT_ROOT)

        if not os.path.exists(fuzzer_dir):
            os.makedirs(fuzzer_dir)
        else:
            for file in os.listdir(fuzzer_dir):
                os.remove(os.path.join(fuzzer_dir, file))
        datesuffix = datetime.now().strftime("%y%m%d")
        with tempfile.TemporaryDirectory() as tmpdir_raw:
            result_name = f"{benchmark}_{datesuffix}.fuzzers"
            tmpdir = os.path.join(tmpdir_raw, result_name)
            os.makedirs(tmpdir, exist_ok=True)
            result_dir = os.path.join(PROJECT_ROOT, rundir, f"gen{evolution_iterations}", "seeds")
            for file in os.listdir(result_dir):
                shutil.copy(os.path.join(result_dir, file), tmpdir)
            tar_result_cmd = ["tar", "-cJf", os.path.join(fuzzer_dir, f"{result_name}.tar.xz"), "-C", tmpdir_raw, result_name]
            subprocess.run(tar_result_cmd, check=True, cwd=PROJECT_ROOT)

        click.echo(f"Fuzzer synthesized for {benchmark} by {target}")
    finally:
        subprocess.run(["sudo", "docker", "stop", "tgi-server"], check=True, cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def produce_glade(benchmark, timelimit: int=600):
    glade_gram_dir = os.path.join(PROJECT_ROOT, "evaluation", "gramgen", benchmark)
    glade_input = os.path.join(glade_gram_dir, "inputs")
    glade_grams = [os.path.join(glade_gram_dir, f) for f in os.listdir(glade_gram_dir) if f.endswith(".gram")]
    assert glade_grams, f"No grammar files found in {glade_gram_dir}"
    if len(glade_grams) > 1:
        glade_grams = [gram for gram in glade_grams if "no-max-depth" in gram]
        assert len(glade_grams) == 1, f"Expected exactly one grammar file with 'no-max-depth' in {glade_gram_dir}, found {len(glade_grams)}"
    glade_gram = glade_grams[0]
    glade_dir = "/home/appuser/glade"
    if os.path.exists(os.path.join(glade_dir, "inputs")):
        shutil.rmtree(os.path.join(glade_dir, "inputs"))
    shutil.copytree(glade_input, os.path.join(glade_dir, "inputs"), dirs_exist_ok=False)
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = os.path.join(tmpdir, f"{benchmark}_glade")
        cmd = [
            "./gradlew", "run", f"--args=\"fuzz -i {glade_gram} -T {timelimit} -o {output_dir}\""
        ]
        subprocess.run(" ".join(cmd), check=True, cwd=glade_dir, shell=True)

        result_dir = os.path.join(PROJECT_ROOT, "extradata", "seeds", "raw", benchmark, "glade")
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
        datetag = datetime.now().strftime("%y%m%d")
        cmd_tar = ["tar", "--zstd", "-cf", os.path.join(result_dir, datetag + ".tar.zst"), f"{benchmark}_glade"]
        subprocess.run(cmd_tar, check=True, env=os.environ.copy(), cwd=tmpdir, stdout=sys.stdout, stderr=sys.stderr)
    click.echo(f"Produced seeds for {benchmark} with GLADE: {os.path.join(result_dir, datetag + '.tar.zst')}")

CONFIG_TEMPLATE = r"""
|[evaluation]
|methods = ['{}']
|benchmarks = [
|    '{}',
|]
|mode = 'normal'
|
|[evaluation.elm]
|exclude = []
|
|[evaluation.grmr]
|exclude = []
|
|[evaluation.isla]
|exclude = []
|
|[evaluation.islearn]
|exclude = ['jsoncpp', 're2']
|
|[evaluation.elmalt]
|exclude = []
|
|[evaluation.elmnospl]
|exclude = []
|
|[evaluation.elmnoinf]
|exclude = []
|
|[evaluation.elmnocomp]
|exclude = []
"""

def produce(fuzzer, benchmark, *, debug=False, timelimit=600):
    info_tarball_suffix = ""
    match fuzzer:
        case "elfuzz":
            fuzzer_name = "elm"
            dir_suffix = ""
            info_tarball_suffix = "_elm"
        case "elfuzz_nofs":
            fuzzer_name = "elmalt"
            dir_suffix = "_alt"
        case "elfuzz_nocp":
            fuzzer_name = "elmnocomp"
            dir_suffix = "_nocomp"
        case "elfuzz_noin":
            fuzzer_name = "elmnoinf"
            dir_suffix = "_noinf"
        case "elfuzz_nosp":
            fuzzer_name = "elmnospl"
            dir_suffix = "_nospl"
        case "grmr":
            fuzzer_name = "grmr"
            dir_suffix = "_grammarinator"
        case "isla":
            fuzzer_name = "isla"
            dir_suffix = "_isla"
        case "islearn":
            fuzzer_name = "islearn"
            dir_suffix = "_islearn"
    if not info_tarball_suffix:
        info_tarball_suffix = dir_suffix
    with tempfile.TemporaryDirectory() as tmpdir:
        config_str = trim_indent(CONFIG_TEMPLATE.format(fuzzer_name, benchmark), delimiter="\n")
        if debug:
            print(f"{config_str=}")
        with open(os.path.join(tmpdir, "config.toml"), "w") as f:
            f.write(config_str)
        os.chown(tmpdir, UID, UID)
        WORKDIR = os.path.join(PROJECT_ROOT, "evaluation", "workdir")
        if os.path.exists(os.path.join(WORKDIR, f"{benchmark}{dir_suffix}")):
            shutil.rmtree(os.path.join(WORKDIR, f"{benchmark}{dir_suffix}"))
        cmd = ["python", os.path.join(WORKDIR, "batchrun.py"), os.path.join(tmpdir, "config.toml")]
        if timelimit != 600:
            env = os.environ.copy() | {"TIME_LIMIT": str(timelimit)}
        else:
            env = os.environ.copy()
        subprocess.run(" ".join(cmd), check=True, env=env, cwd=WORKDIR, stdout=sys.stdout,
                       shell=True, stderr=sys.stderr, user=USER)
    if not (fuzzer.startswith("elfuzz") and fuzzer != "elfuzz"):
        click.echo("Generation done. Now we have to collect all the test cases to one place. This may take a while...")
        SEED_DIR = os.path.join(WORKDIR, f"{benchmark}{dir_suffix}", "out")
        with tempfile.TemporaryDirectory() as tmpdir:
            collect_dir = os.path.join(tmpdir, f"{benchmark}{info_tarball_suffix}", "seeds")
            os.makedirs(collect_dir, exist_ok=True)
            for dir in os.listdir(SEED_DIR):
                p = os.path.join(SEED_DIR, dir)
                if not os.path.isdir(p):
                    continue
                for file in os.listdir(p):
                    file_p = os.path.join(p, file)
                    target_file = os.path.join(collect_dir, f"{dir}_{file}")
                    shutil.move(file_p, target_file)
            result_dir = os.path.join(PROJECT_ROOT, "extradata", "seeds", "raw", benchmark, fuzzer_name)
            if not os.path.exists(result_dir):
                os.makedirs(result_dir)
            datetag = datetime.now().strftime("%y%m%d")
            cmd_tar = ["tar", "--zstd", "-cf", os.path.join(result_dir, datetag + ".tar.zst"), f"{benchmark}{info_tarball_suffix}"]
            subprocess.run(cmd_tar, check=True, env=os.environ.copy(), cwd=tmpdir, stdout=sys.stdout, stderr=sys.stderr)
            click.echo(f"Produced seeds for {benchmark} with {fuzzer} fuzzer collected in {os.path.join(result_dir, datetag + '.tar.zst')}")
    produce_info_dir = os.path.join(PROJECT_ROOT, "extradata", "produce_info")
    if not os.path.exists(produce_info_dir):
        os.makedirs(produce_info_dir)
    cmd_tar_raw = ["tar", "--zstd", "-cf", os.path.join(produce_info_dir, f"{benchmark}{info_tarball_suffix}.tar.zst"), f"{benchmark}{dir_suffix}"]
    subprocess.run(cmd_tar_raw, check=True, env=os.environ.copy(), cwd=WORKDIR, stdout=sys.stdout, stderr=sys.stderr,)
    click.echo(f"Info during seed test case generation in: {os.path.join(produce_info_dir, f'{benchmark}{info_tarball_suffix}.tar.zst')}")