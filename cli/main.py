import click
import re
import subprocess
import os
import sys
import toml

MAIN_CLI_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "."))

sys.path.insert(0, MAIN_CLI_DIR)
import download as download_mod
from common import PROJECT_ROOT, USER, trim_indent

from pre_experiments import (
    synthesize_fuzzer,
    synthesize_grammar,
    synthesize_semantics,
    produce,
    produce_glade
)
from minimize import minimize_command
from rq1 import rq1_seed_cov_cmd, rq1_afl_run, rq1_afl_update


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

@cli.command(name="sync_repo", hidden=True)
def sync_repo():
    cmd_stash = ["git", "stash"]
    subprocess.run(cmd_stash, check=True, cwd=PROJECT_ROOT)
    cmd_pull = ["git", "pull", "--rebase"]
    subprocess.run(cmd_pull, check=True, cwd=PROJECT_ROOT)

DEFAULT_TGI_WAITING = 1200

@cli.command(name="synth", help="Synthesize input generators by ELFuzz and its four variants, mine grammars by GLADE, or learn semantic constraints by ISLearn.")
@click.option("--target", "-T", required=True, type=click.Choice(
    ["fuzzer.elfuzz", "fuzzer.elfuzz_nofs", "fuzzer.elfuzz_nocp", "fuzzer.elfuzz_noin", "fuzzer.elfuzz_nosp",
     "grammar.glade", "semantics.islearn"]
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
@click.option("--no-select-semantic-constraints", "--no-select", is_flag=True, default=False,
              help="This option only works for semantics.islearn. If this option is set, the user should manually \
select one semantic constraint from the mined semantic constraints \
and put it into evaluation/islearn_adapt/selected/<benchmark>_isla<timetag>.isla. If this option is not set, \
a random one from the constraints with the best recall and precision will be selected from the mined constraints and put into the file.")
@click.option("--debug", is_flag=True, default=False, hidden=True)
def synthesize(target, benchmark, tgi_waiting, debug, no_select_semantic_constraints):
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
        case "semantic.islearn":
            synthesize_semantics(benchmark, no_select=no_select_semantic_constraints)
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
@click.option("--only-relocate", "-s", is_flag=True, default=False,
              help="Only relocate the files from the cache directory to the data directory without downloading and unziping them again.")
def download(ignore_cache: bool, only_relocate: bool):
    click.echo("Downloading data files needed by the experiments...")
    download_mod.download_data(ignore_cache=ignore_cache, only_relocate=only_relocate)

@cli.command(name="info", help="Show information about the Docker image.")
def info():
    cmd = ["git", "rev-parse", "--short", "HEAD"]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
    commit_hash = result.stdout.strip()
    click.echo(f"Docker image built from the ELFuzz project at revision {commit_hash}")
    click.echo(f"Project root in the container: {PROJECT_ROOT}")

@cli.command(name="produce", help="Generate seed test cases")
@click.option("--fuzzer", "-T", required=True, type=click.Choice(
    ["elfuzz", "elfuzz_nofs", "elfuzz_nocp", "elfuzz_noin", "elfuzz_nosp", "isla", "islearn", "grmr", "glade"]
))
@click.argument("benchmark", required=True, type=click.Choice(
    ["jsoncpp", "libxml2", "re2", "librsvg", "cvc5", "sqlite3", "cpython3"]
))
@click.option("--debug", is_flag=True, default=False, hidden=True)
def produce_command(fuzzer: str, benchmark: str, debug: bool):
    match fuzzer, benchmark:
        case ("islearn", "jsoncpp") | ("islearn", "re2"):
            click.echo(f"Fuzzer {fuzzer} is not supported for benchmark {benchmark}.")
            return
    match fuzzer:
        case "glade":
            produce_glade(benchmark)
        case "elfuzz" | "elfuzz_nofs" | "elfuzz_nocp" | "elfuzz_noin" | "elfuzz_nosp" | "isla" | "islearn" | "grmr":
            produce(fuzzer, benchmark, debug=debug)
        case _:
            click.echo(f"Unknown fuzzer: {fuzzer}. Supported fuzzers are: elfuzz, elfuzz_nofs, elfuzz_nocp, elfuzz_noin, elfuzz_nosp, isla, islearn, grmr, glade.")

@cli.command(name="minimize", help="Minimize test cases and (optionally) prepend random control bytes.")
@click.option("--all", "-a", is_flag=True, default=False,
              help="Minimize all benchmark x fuzzer combinations.")
@click.option("--fuzzer", "-T", required=True, type=click.Choice(
    ["elfuzz", "isla", "islearn", "grmr", "glade"]
))
@click.argument("benchmark", required=False, type=click.Choice(
    ["jsoncpp", "libxml2", "re2", "librsvg", "cvc5", "sqlite3", "cpython3"]
), default=None)
def minimize(all, fuzzer, benchmark):
    if not all and benchmark is None:
        click.echo("You must specify a benchmark if you don't use --all.")
        return
    match fuzzer, benchmark:
        case ("islearn", "jsoncpp") | ("islearn", "re2"):
            click.echo(f"Fuzzer {fuzzer} is not supported for benchmark {benchmark}.")
            return
    minimize_command(all=all, fuzzer=fuzzer, benchmark=benchmark)

@cli.group(name="run", help="Run ELFuzz experiments.")
def run():
    pass

@run.command(name="rq1.seed_cov", help=trim_indent("""
    |Collect the seed coverage presented in Figure 7 in RQ1.
    |Note that if you use the original data we provide on Figshare,
    |the command will use `afl-showmap` to re-collect the information,
    |as in our original experiments we didn't keep the seed coverage collected during generation.
    |Otherwise, it will directly use the seed coverage collected during generation.
"""))
@click.option("--fuzzer", "-T", required=True, type=click.Choice(
    ["elfuzz", "grmr", "glade", "isla", "islearn"]
))
@click.argument("benchmark", required=True, type=click.Choice(
    ["jsoncpp", "re2", "sqlite3", "cpython3", "libxml2", "librsvg", "cvc5"]
))
def rq1_seed_cov(fuzzer, benchmark):
    if fuzzer == "islearn" and benchmark in ["jsoncpp", "re2"]:
        click.echo(f"Fuzzer {fuzzer} is not supported for benchmark {benchmark}.")
        return
    rq1_seed_cov_cmd(fuzzer, benchmark)

@run.command(name="rq1.afl", help="Run the AFL++ fuzzing compaigns for Figure 8 in RQ1 on BENCHMARKS (represented as a list separated by `,`).")
@click.option("--fuzzers", "-T", type=str, help="Fuzzer list separated by `,`.", required=True)
@click.option("--repeat", "-r", type=int, default=1, show_default=True, required=False,
              help="Repeat the AFL++ fuzzing campaigns for each fuzzer and benchmark.")
@click.option("--debug", is_flag=True, default=False, hidden=True,)
@click.argument("benchmarks", type=str, required=True)
def rq1_afl(fuzzers, benchmarks, repeat):
    fuzzer_list = [f.strip() for f in fuzzers.split(",")]
    benchmark_list = [b.strip() for b in benchmarks.split(",")]
    for fuzzer in fuzzer_list:
        if fuzzer not in ["elfuzz", "grmr", "glade", "isla", "islearn"]:
            click.echo(f"Fuzzer {fuzzer} is not supported.")
            continue
        for benchmark in benchmark_list:
            if benchmark not in ["jsoncpp", "re2", "sqlite3", "cpython3", "libxml2", "librsvg", "cvc5"]:
                click.echo(f"Benchmark {benchmark} is not supported.")
                continue
    entries = rq1_afl_run(fuzzer_list, benchmark_list, repeat=repeat, debug=debug)
    rq1_afl_update(entries)

if __name__ == "__main__":
    os.chdir(PROJECT_ROOT)
    sys.argv[0] = "elfuzz"
    cli(max_content_width=get_terminal_width())