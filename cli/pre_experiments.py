import os
import subprocess
from datetime import datetime
import sys
import shutil
import click
from common import PROJECT_ROOT, CLI_DIR, USER

def synthesize_grammar(benchmark):
    inputs_dir = os.path.join(PROJECT_ROOT, "evaluation", "gramgen", benchmark, "inputs")

    if os.path.exists(inputs_dir):
        shutil.rmtree(inputs_dir)

    GLADE_DIR = os.path.join("/", "home", USER, "glade")
    target_dir = os.path.join(GLADE_DIR, "inputs")
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

    learn_cmd = ["./gradlew", "run", "--args", f"learn -rd 100 -l 0-100 '{oracle_cmd}'"]
    click.echo(f"Running GLADE to mine grammar for {benchmark} (may needs several hours)...")
    subprocess.run(learn_cmd, check=True, env=os.environ.copy() | {"JAVA_HOME": "/home/appuser/.sdkman/candidates/java/current/"},
                   cwd=GLADE_DIR, user=USER, shell=True)

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