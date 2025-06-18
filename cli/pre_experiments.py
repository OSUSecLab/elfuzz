import os
import subprocess
from datetime import datetime
import sys
import shutil
import click
from common import PROJECT_ROOT, CLI_DIR, USER
from datetime import datetime
import tempfile

def synthesize_semantics(benchmark):
    click.echo(f"Preparing environments...")
    cmd_prepare_base = ["sudo", "python", os.path.join(PROJECT_ROOT, "prepare_fuzzbench.py")]
    match benchmark:
        case "jsoncpp" | "libxml2" | "re2" | "sqlite3":
            pass
        case "cpython3" | "librsvg":
            cmd_prepare_base += ["-d", "/home/appuser/oss-fuzz", "-t", "oss-fuzz"]
        case "cvc5":
            cmd_prepare_base += ["-t", "docker"]
    env = os.environ.copy() | {"ELMFUZZ_RUNDIR": f"preset/{benchmark}"}
    subprocess.run(" ".join(cmd_prepare_base), check=True, env=env, shell=True,
                   cwd=PROJECT_ROOT, stdout=sys.stdout, stderr=sys.stderr, user=USER)
    cmd_prepare = ["sudo", "python", os.path.join(PROJECT_ROOT, "evaluation", "islearn_adapt", "prepare_islearn.py"), benchmark]
    subprocess.run(" ".join(cmd_prepare), shell=True, check=True, env=env, cwd=PROJECT_ROOT, stdout=sys.stdout, stderr=sys.stderr, user=USER)
    click.echo(f"Mining semantic constraints...")
    stored_dir = os.path.join(PROJECT_ROOT, "extradata", "islearn_constraints")
    if not os.path.exists(stored_dir):
        os.makedirs(stored_dir)
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_mine = ["docker", "run", "--rm", "-v", f"{tmpdir}:/tmp/semantics/", f"elmfuzz/{benchmark}_islearn",
                    "python", "infer_semantics.py", "-o", f"/tmp/semantics/{benchmark}.json"]
        subprocess.run(cmd_mine, check=True, env=os.environ.copy(), cwd=PROJECT_ROOT, stdout=sys.stdout, stderr=sys.stderr)
        existing = [os.path.join(stored_dir, f) for f in os.listdir(stored_dir) if f.endswith(".json") and benchmark in f]
        assert len(existing) <= 1, f"Expected at most one existing semantic constraints file for {benchmark}, found {len(existing)}"
        if existing:
            os.remove(existing[0])
            click.echo(f"Storing semantic constraints for {benchmark}...")
        shutil.copy(os.path.join(tmpdir, f"{benchmark}.json"), os.path.join(stored_dir, f"{benchmark}.json"))
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
    for file in os.listdir(gram_dir):
        if file.endswith(".gram"):
            os.remove(os.path.join(gram_dir, file))
    gram_file_generated = [file for file in os.listdir(gram_dir) if file.endswith(".gram")]
    assert len(gram_file_generated) == 1, f"Expected exactly one grammar file, found {len(gram_file_generated)}"

    shutil.move(os.path.join(gram_dir, gram_file_generated[0]), os.path.join(gram_dir, gram_file_generated[0]))
    click.echo(f"Grammar for {benchmark} synthesized successfully: {os.path.join(gram_dir, gram_file_generated[0])}.")

def synthesize_fuzzer(target, benchmark, *, tgi_waiting=600, debug=False):
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

    cmd_tgi = ["sudo", os.path.join(PROJECT_ROOT, "start_tgi_servers.sh")]
    click.echo(f"Starting the text-gneration-inference server. This may take a while as it has to download the model...")

    try:
        tgi_p = subprocess.Popen(" ".join(cmd_tgi), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=PROJECT_ROOT, user=USER)
        start = datetime.now()
        while True:
            if tgi_p.poll() is not None:
                raise RuntimeError("TGI server failed to start.")
            if (datetime.now() - start).total_seconds() > tgi_waiting:
                break
            assert tgi_p.stdout is not None, "TGI server stdout is None."
            line = tgi_p.stdout.readline().decode("utf-8").strip()
            if line:
                print(line, flush=True)
        click.echo("Text-generation-inference server started.")
    except Exception as e:
        if debug:
            click.echo(f"Error starting TGI server: {e}")
            click.echo(f"It will be ignored in the debug mode.")
        else:
            raise e

    rundir = os.path.join("preset", benchmark)
    cmd = ["sudo", os.path.join(PROJECT_ROOT, "all_gen.sh"), rundir]
    subprocess.run(" ".join(cmd), check=True, env=env, shell=True, user=USER, cwd=PROJECT_ROOT)

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
    with tempfile.TemporaryDirectory() as tmpdir:
        result_name = f"{benchmark}_{datesuffix}.fuzzers"
        tmpdir = os.path.join(tmpdir, result_name)
        os.makedirs(tmpdir, exist_ok=True)
        result_dir = os.path.join(PROJECT_ROOT, rundir, "gen50", "seeds")
        for file in os.listdir(result_dir):
            shutil.copy(os.path.join(result_dir, file), tmpdir)
        tar_result_cmd = ["tar", "-cJf", os.path.join(fuzzer_dir, f"{result_name}.tar.xz"), "-C", tmpdir, result_name]
        subprocess.run(tar_result_cmd, check=True, cwd=PROJECT_ROOT)

    click.echo(f"Fuzzer synthesized for {benchmark} by {target}")