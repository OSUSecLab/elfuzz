import os
import datetime as dt
import subprocess
from math import ceil
import json
import sys

# Create tmp directory if it doesn\'t exist
if not os.path.exists("tmp"):
    os.makedirs("tmp")

if sys.version_info <= (3, 10):
    TIMETAG = dt.datetime.utcnow().strftime('%y_%m_%d__%H_%M_%S')
else:
    TIMETAG = dt.datetime.now(dt.UTC).strftime('%y_%m_%d__%H_%M_%S')

# Create the tar.xz file
archive_name = f"tmp/elfuzz_docker_{TIMETAG}.tar"

cmd = ["docker", "save", "-o", archive_name, "ghcr.io/osuseclab/elfuzz:25.08.0"]
subprocess.run(cmd)

cmd = ["zstd", "-o", f"{archive_name}.zst", archive_name]
subprocess.run(cmd)

os.remove(archive_name)

archive_name = f"{archive_name}.zst"

print(f"Archive '{archive_name}' created successfully.")

archive_size = os.path.getsize(archive_name)
print(f"Archive size: {archive_size} bytes")

GB = 1024 * 1024 * 1024

PART_NUM = ceil(archive_size / (0.5 * GB))

if PART_NUM == 1:
    print(f"Archive is less than 1GB, no need to split")
    exit(0)

print(f"Splitting into {PART_NUM} parts")

cmd = ["split", "-b", f"512M", archive_name, f"tmp/elfuzz_docker_{TIMETAG}.tar.zst.part"]
subprocess.run(cmd)

print(f"Splitted")

os.remove(archive_name)

files = os.listdir("tmp")

part_files = [f for f in files if f.startswith(f"elfuzz_docker_{TIMETAG}.tar.zst.part")]

part_files.sort()

# Docker will pull the repo from GtiHub
cmd = ["git", "log", "-1", "origin/main"]
output = subprocess.check_output(cmd).decode("utf-8")
commit = output.split("\n")[0].split(" ")[1]

with open("tmp/docker_metadata.json", "w") as f:
    json.dump({
        "timetag": TIMETAG,
        "commit": commit,
        "part_files": part_files,
    }, f, indent=2)
