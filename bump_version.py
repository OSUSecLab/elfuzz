import os
import sys

PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))

FILES_TO_UPDATE = [
    os.path.join(PROJECT_ROOT, "README.md"),
    os.path.join(PROJECT_ROOT, "tar_docker.py")
]

VERSION_HISTORY = os.path.join(PROJECT_ROOT, "replication_package.version.history")

if __name__ == '__main__':
    new_version = sys.argv[1]
    with open(VERSION_HISTORY, "r") as version_history_file:
        version_history_records = [line.strip() for line in version_history_file.readlines()]
        old_version = version_history_records[0].strip()
    for file in FILES_TO_UPDATE:
        with open(file, "r") as f:
            content = f.read()
        content = content.replace(old_version, new_version)
        with open(file, "w") as f:
            f.write(content)
    with open(VERSION_HISTORY, "w") as version_history_file:
        version_history_file.write("\n".join([new_version] + version_history_records))
