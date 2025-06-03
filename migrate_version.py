import os

VERSION_HISTORY = []

with open("replication_package.version.history", "r") as f:
    for line in f:
        if not line.strip():
            continue
        VERSION_HISTORY.append(line.strip())
if len(VERSION_HISTORY) <= 1:
    exit(0)

files = os.listdir(".")

previous_version = VERSION_HISTORY[-2]
current_version = VERSION_HISTORY[-1]

for file in files:
    if file.endswith(".py") or file.endswith(".md") or file.endswith(".sh"):
        with open(file, "r") as f:
            content = f.read()
        content = content.replace(previous_version, current_version)
        with open(file, "w") as f:
            f.write(content)
