import os
import subprocess
import shutil

ROOT = os.path.realpath(os.path.dirname(__file__))

tarball_path = os.path.join(ROOT, "tmp", "elfuzz_src.tar")

cmd = ["git", "archive", "--format=tar", f"--output={tarball_path}", "HEAD"]
subprocess.run(cmd, check=True)
cmd = ["zstd", "-15", "-T0", tarball_path, "-o", f"{tarball_path}.zst"]
subprocess.run(cmd, check=True)
os.remove(tarball_path)
tarball_path = f"{tarball_path}.zst"
print(f"Archive '{tarball_path}' created successfully.")

shutil.copy(os.path.join(ROOT, "artifacts_readme.md"), os.path.join(ROOT, "tmp", "README.md"))
print("Artifacts README copied to tmp directory.")
