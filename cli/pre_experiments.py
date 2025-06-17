import os
import subprocess
import sys
import time
import click
from common import PROJECT_ROOT, CLI_DIR

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

    cmd_tgi = ["/usr/bin/bash", os.path.join(PROJECT_ROOT, "start_tgi_servers.sh")]
    click.echo(f"Starting the text-gneration-inference server. This may take a while as it has to download the model...")

    try:
        tgi_p = subprocess.Popen(cmd_tgi, stdout=sys.stdout, stderr=sys.stderr, env=env)
        time.sleep(tgi_waiting) # It is hard to know whether the TGI server is ready, so we require the user to provide an estimation.
        click.echo("Text-generation-inference server started.")
        tgi_p.stdout = None
        tgi_p.stderr = None
    except Exception as e:
        if debug:
            click.echo(f"Error starting TGI server: {e}")
            click.echo(f"It will be ignored in the debug mode.")
        else:
            raise e

    rundir = os.path.join(PROJECT_ROOT, "preset", benchmark) + "/"
    cmd = ["/usr/bin/bash", os.path.join(PROJECT_ROOT, "all_gen.sh"), rundir]
    subprocess.run(cmd, check=True, env=env)