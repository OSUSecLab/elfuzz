import click
import re
import subprocess
import os
import sys
import toml

MAIN_CLI_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "."))

sys.path.insert(0, MAIN_CLI_DIR)
import download as download_mod
from common import PROJECT_ROOT

from pre_experiments import synthesize_fuzzer, synthesize_grammar


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
    fuzzdata_dir = "/tmp/fuzzdata"
    if not os.path.exists(fuzzdata_dir):
        os.makedirs(fuzzdata_dir)
    cmd = [
        "/usr/bin/bash", "/home/appuser/elmfuzz/.devcontainer/setup_docker.sh"
    ]
    subprocess.run(cmd, check=True)
    click.echo("Done! Now please restart the container manually.")

DEFAULT_TGI_WAITING = 1200

@cli.command(name="synth", help="Synthesize input generators by ELFuzz and its four variants, mine grammars by GLADE, or learn semantic constraints by ISLearn.")
@click.option("--target", "-T", required=True, type=click.Choice(
    ["fuzzer.elfuzz", "fuzzer.elfuzz_nofs", "fuzzer.elfuzz_nocp", "fuzzer.elfuzz_noin", "fuzzer.elfuzz_nosp",
     "grammar.glade", "semantic.islearn"]
))
@click.argument("benchmark", required=True, type=click.Choice(
    ["jsoncpp", "libxml2", "re2", "librsvg", "cvc5", "sqlite3", "cpython3"]
))
@click.option("--tgi-waiting", "-w", type=int, default=DEFAULT_TGI_WAITING, show_default=True,
              help="This option only works for targets <fuzzer.*>. It provides the estimated time in seconds to wait for the text-generation-inference server to be ready (after downloading the model files and \
starting the service ). We need the user to provide the estimation as it is hard to know the \
precise status of the server at runtime.  The default value should \
be proper if you are in an area with a typical network condition (i.e., outside mainland China) and start the server for the first time. \
If you have already started the server before, the cached model files can significantly shorten the waiting time. You may provide a smaller \
value for the estimation.")
@click.option("--debug", is_flag=True, default=False, hidden=True)
def synthesize(target, benchmark, tgi_waiting, debug):
    match target, benchmark:
        case ("semantic.islearn", "jsoncpp"):
            click.echo("The JSON format doesn't need semantic constraints, so no synthesis will be conducted.")
            return
    match target:
        case "fuzzer.elfuzz" | "fuzzer.elfuzz_nofs" | "fuzzer.elfuzz_nocp" | "fuzzer.elfuzz_noin" | "fuzzer.elfuzz_nosp":
            synthesize_fuzzer(target.split(".")[1], benchmark, tgi_waiting=tgi_waiting, debug=debug)
            return
        case "grammar.glade":
            synthesize_grammar(benchmark)
            return
        case _:
            click.echo(f"Target {target} for `synth` hasn't been implemented yet.")
            return

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
        click.echo(trim_indent("""
            |logging.enable_email (default: False): Enable email notifications for logging.
            |logging.email_send (default: dummy@gmail.com): Email address to send notifications.
            |logging.email_receive (default: dummy@gmail.com): Email address to receive notifications.
            |logging.email_smtp_server (default: smtp.gmail.com): SMTP server for sending emails.
            |logging.email_smtp_port (default: 587): SMTP port for sending emails.
            |logging.email_smtp_password (default: dummypassword): SMTP password for sending emails.
            |tgi.huggingface_token (default: None): Hugging Face token for accessing private models.
        """, delimiter="\n"))
    elif set is not None:
        config = toml.load(os.path.join(MAIN_CLI_DIR, "config.toml"))
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
            case "tgi.huggingface_token":
                token_path = "/root/.config/huggingface"
                if not os.path.exists(token_path):
                    os.makedirs(token_path, exist_ok=True)
                with open(os.path.join(token_path, "token"), "w") as f:
                    f.write(value)
                click.echo(f"{key} := {value}")
                return
            case _:
                click.echo(f"Unknown configuration option: {key}")
        toml.dump(config, os.path.join(MAIN_CLI_DIR, "config.toml"))
        click.echo(f"{key} := {value}.")
    elif get is not None:
        config = toml.load(os.path.join(MAIN_CLI_DIR, "config.toml"))
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
            case "tgi.huggingface_token":
                token_path = "/root/.config/huggingface/token"
                if not os.path.exists(token_path):
                    click.echo("None")
                with open(token_path, "r") as f:
                    value = f.read().strip()
            case _:
                click.echo(f"Unknown configuration option: {get}")
                return
        click.echo(f"{get} == {value}")
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
    click.echo("Downloading data files needed by the experiments...")
    download_mod.download_data(ignore_cache=ignore_cache)

@cli.command(name="info", help="Show information about the Docker image.")
def info():
    cmd = ["git", "rev-parse", "--short", "HEAD"]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
    commit_hash = result.stdout.strip()
    click.echo(f"Docker image built from the ELFuzz project at revision {commit_hash}")
    click.echo(f"Project root in the container: {PROJECT_ROOT}")

if __name__ == "__main__":
    os.chdir(PROJECT_ROOT)
    sys.argv[0] = "elfuzz"
    cli(max_content_width=get_terminal_width())