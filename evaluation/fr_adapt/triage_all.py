import click
import os
import subprocess

PWD = os.path.dirname(os.path.abspath(__file__))

TRIAGE_ONE = os.path.join(PWD, "triage.py")

@click.command()
@click.option("--root", "-i", type=str, required=True)
@click.option("--output", "-o", type=str, default="triage")
@click.option("--parallel", "-j", type=int, default=10)
@click.option("--force-rerun", type=str, default="")
def main(root, output, parallel, force_rerun):
    force_rerun_record = {}
    for token in force_rerun.split(","):
        benchmark, fuzzer, rep = token.split("_")
        rep_n = int(rep)
        if rep_n not in force_rerun_record:
            force_rerun_record[rep_n] = []
        force_rerun_record[rep_n].append((benchmark, fuzzer))
    for i in range(1, 11):
        print(f"Triage {i} / 10")
        cmd = [
            "python",
            TRIAGE_ONE,
            "--force-rerun",
            ",".join([f"{b}_{f}" for b, f in force_rerun_record.get(i, [])]),
            "--afl-root",
            os.path.join(root, str(i)),
            "--output",
            os.path.join(output, str(i)),
            "--parallel",
            str(parallel),
            "-c"
        ]
        subprocess.run(cmd)

if __name__ == "__main__":
    main()