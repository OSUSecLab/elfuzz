import click
import re
import subprocess
import os
import sys
import toml
import importlib

PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
CLI_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "."))

sys.path.insert(0, CLI_DIR)
from . import download as download_mod


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

# @cli.command(name="synthesize", help="Synthesize input generators.")
# def synthesize():
#     click.echo("Synthesis not automated yet in this version.")

@cli.command(name="config", help="Manage configuration.")
@click.option("list_", "--list", "-l", is_flag=True, help="List all configuration options.")
@click.option("--set", "-s", type=(str, str), help="Set a configuration option.", default=None)
@click.option("--get", "-g", type=str, help="Get a configuration option.", default=None)
def config(list_: bool, set: tuple[str, str], get: str):
    assert ((list_ is True and set is None and get is None) or
            (list_ is False and set is not None and get is None) or
            (list_ is False and set is None and get is not None)), \
        "You can only use one of --list, --set, or --get."
    if list_:
        click.echo("logging.enable_email (default: False): Enable email notifications for logging.")
        click.echo("logging.email_send (default: dummy@gmail.com): Email address to send notifications.")
        click.echo("logging.email_receive (default: dummy@gmail.com): Email address to receive notifications.")
        click.echo("logging.email_smtp_server (default: smtp.gmail.com): SMTP server for sending emails.")
        click.echo("logging.email_smtp_port (default: 587): SMTP port for sending emails.")
        click.echo("logging.email_smtp_password (default: dummypassword): SMTP password for sending emails.")
    elif set is not None:
        config = toml.load(os.path.join(CLI_DIR, "config.toml"))
        key, value = set
        match key:
            case "logging.enable_email":
                config["logging"]["enable_email"] = str(value)
            case "logging.email_send":
                config["logging"]["email_send"] = value
            case "logging.email_receive":
                config["logging"]["email_receive"] = value
            case "logging.email_smtp_server":
                config["logging"]["email_smtp_server"] = value
            case "logging.email_smtp_port":
                config["logging"]["email_smtp_port"] = int(value)
            case "logging.email_smtp_password":
                config["logging"]["email_smtp_password"] = value
            case _:
                click.echo(f"Unknown configuration option: {key}")
        toml.dump(config, os.path.join(CLI_DIR, "config.toml"))
        click.echo(f"Set {key} to {value}.")
    elif get is not None:
        config = toml.load(os.path.join(CLI_DIR, "config.toml"))
        match get:
            case "logging.enable_email":
                value = config["logging"]["enable_email"]
            case "logging.email_send":
                value = config["logging"]["email_send"]
            case "logging.email_receive":
                value = config["logging"]["email_receive"]
            case "logging.email_smtp_server":
                value = config["logging"]["email_smtp_server"]
            case "logging.email_smtp_port":
                value = config["logging"]["email_smtp_port"]
            case "logging.email_smtp_password":
                value = config["logging"]["email_smtp_password"]
            case _:
                click.echo(f"Unknown configuration option: {get}")
                return
        click.echo(f"{get} = {value}")
@cli.command(name="cluster_synth", help="Get instructions about synthesizing input generators on a GPU cluster.")
def synthesize_on_cluster():
    instructions = trim_indent("""
                               |Running the synthesis on a GPU cluster is quite cubersome and has yet to be automated.
                               |Please see docs/synthesize_on_cluster.md or https://github.com/cychen2021/elfuzz/blob/main/docs/synthesize_on_cluster.md for instructions.
                               """, delimiter="\n")
    click.echo(instructions)

@cli.command(name="download", help="Download large binary files stored on Figshare.")
@click.option("--ignore-cache", is_flag=True, default=False,)
def download(ignore_cache: bool):
    click.echo("This command should download the binaries and other data from Figshare and put them into the right places in the ELFuzz project directory.")
    click.echo("However, this command has not been implemented yet. You should do it manually.")
    click.echo("You may need to check the error message when running an experiment script to figure out what files to put where.")
    download_mod.download_data(ignore_cache=ignore_cache)

if __name__ == "__main__":
    sys.argv[0] = "elfuzz"
    cli(max_content_width=get_terminal_width())