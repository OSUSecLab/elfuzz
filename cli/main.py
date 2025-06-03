import click
import re
import subprocess
import os
import sys
import tqdm

PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
CLI_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "."))

def trim_indent(s: str, *, delimiter: str = " ") -> str:
    ended_with_newline = s.endswith("\n")
    lines = s.removesuffix("\n").split("\n")
    new_lines = []
    for l in lines:
        m = re.match(r"^(\s*|).*$", l)
        if m:
            to_trim = len(m.group(1))
            new_lines.append(l[to_trim+1:])
        else:
            new_lines.append(l)
    if len(new_lines) > 0:
        if not new_lines[0].strip():
            new_lines.pop(0)
    if len(new_lines) > 1:
        if not new_lines[-1].strip():
            new_lines.pop(-1)
    return delimiter.join(new_lines) + ("\n" if ended_with_newline else "")

def get_terminal_width():
    """
    Returns the width of the terminal in characters.
    """
    try:
        columns = os.get_terminal_size().columns
        return columns
    except OSError:
        # If not running in a terminal, return a default width
        return 80

@click.group(name="elfuzz")
def cli():
    pass

@cli.command(name="setup", help=trim_indent("""
             |Setup the Docker container to enable sibling containers.
             |See https://stackoverflow.com/questions/39151188/is-there-a-way-to-start-a-sibling-docker-container-mounting-volumes-from-the-hos for more information."""))
@click.help_option("--help", "-h")
def setup():
    y = click.confirm(trim_indent("""
                  |This command will run a script to enable sibling containers.
                  |You have to restart the container manually after this command to make the changes take effect.
                  |Make sure you didn't launch the container with the `--rm` option.
                  """, delimiter="\n"))
    if not y:
        return
    click.echo("Setting up...")
    cmd = [
        "/usr/bin/bash", "/home/appuser/elmfuzz/.devcontainer/setup_docker.sh"
    ]
    subprocess.run(cmd, check=True)
    click.echo("Done! Now please restart the container manually.")

@cli.command(name="synthesize", help="Synthesize input generators.")
def synthesize():
    ...

@cli.command(name="cluster_synth", help="Get instructions about synthesizing input generators on a GPU cluster.")
def synthesize_on_cluster():
    instructions = trim_indent("""
                               |Running the synthesis on a GPU cluster is quite cubersome and has yet to be automated.
                               |Please see docs/synthesize_on_cluster.md or https://github.com/cychen2021/elfuzz/blob/main/docs/synthesize_on_cluster.md for instructions.
                               """, delimiter="\n")
    click.echo(instructions)

@cli.command(name="download", help="Download large binary files stored on Zenodo.")
@click.option("--local-copy", "-l", is_flag=True, default=False,)
def download(local_copy: bool):
    click.echo("Downloading...")
    FIGSHARE_URL = "https://doi.org/10.6084/m9.figshare.29177162"
    LOCAL_DIR = "/tmp/elfuzz_data_cache"
    ...

if __name__ == "__main__":
    sys.argv[0] = "elfuzz"
    cli(max_content_width=get_terminal_width())