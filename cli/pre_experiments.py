import os
import subprocess
from datetime import datetime
import sys
import click
from common import PROJECT_ROOT, CLI_DIR, USER

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