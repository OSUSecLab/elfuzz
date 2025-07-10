import json
import os
import requests
from dataclasses import dataclass
import hashlib
from tqdm import tqdm
import click
import subprocess
import shutil
from typing import Callable, Literal

from common import PROJECT_ROOT, CLI_DIR

ZENODO_API_BASE = "https://zenodo.org/api"
DEFAULT_RECORD_ID = "15833146"
CACHE_DIR = "/tmp/cache"
TMP_UNZIP_DIR = "/tmp/unzip"

RELOCATE_HOOK = Callable[[str], None]

@dataclass
class RelocateTo:
    from_: str
    to: str
    hook: RELOCATE_HOOK | None
    kind: Literal["tarball", "contents", "normal"]

def path_is_contents(path: str) -> bool:
    return path.endswith("*")

def path_is_directory(path: str) -> bool:
    return path.endswith("/")

def load_relocate_info() -> list[RelocateTo]:
    with open(os.path.join(CLI_DIR, "relocate.json")) as f:
        hook = None
        result = []
        for item in json.load(f):
            from_ = item["from"]
            to = item["to"]
            is_contents = path_is_contents(from_)
            if "is_tarball" in item:
                is_tarball = item["is_tarball"]
            else:
                is_tarball = False
            match is_contents, is_tarball:
                case True, False:
                    kind = "contents"
                case False, True:
                    kind = "tarball"
                case False, False:
                    kind = "normal"
                case True, True:
                    raise ValueError("A path cannot be both contents and tarball at the same time")
            hook = None
            if "hook" in item:
                hook = globals().get(item["hook"], None)
                assert hook is not None, f"Hook {item['hook']} not found"
            result.append(RelocateTo(from_=from_, to=to, hook=hook, kind=kind))
        return result

def truncate_prefix(relocated_path: str):
    dirs = os.listdir(relocated_path)
    assert len(dirs) == 1, "There should be exactly one directory in the relocated path"
    subdir = dirs[0]
    for item in os.listdir(os.path.join(relocated_path, subdir)):
        shutil.move(os.path.join(relocated_path, subdir, item), os.path.join(relocated_path, item))

def unpack_islearn_constraints(relocated_path: str):
    constraints_dir = os.path.join(relocated_path, "islearn_constraints")
    files = [os.path.join(constraints_dir, f) for f in os.listdir(constraints_dir) if f.endswith(".json.tar.xz")]
    for file in files:
        cmd = ["tar", "-xJf", file, "-C", constraints_dir]
        subprocess.run(cmd, check=True)
        os.remove(file)

def rename_islearn_ground_truth(relocated_path: str):
    shutil.move(os.path.join(relocated_path, "fr_ground_truth"), os.path.join(relocated_path, "oracles"))

def relocate(data_dir: str):
    relocate_info = load_relocate_info()
    count = 1
    for item in relocate_info:
        click.echo(f"[{count}/{len(relocate_info)}] Relocating {item.from_} to {item.to}...")
        count += 1
        src = os.path.join(data_dir, item.from_)
        dst = os.path.join(PROJECT_ROOT, item.to)

        dst_dir = os.path.dirname(dst)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)

        if (item.kind != "contents" and not os.path.exists(src) or
            item.kind == "contents" and not os.path.exists(src.removesuffix("*"))):
            click.echo(f"WARNING: Source path {src} does not exist. Skipping.")
            continue

        match item.kind:
            case "contents":
                assert path_is_directory(dst), f"Target {dst} must be a directory for contents relocation"
                src_dir = src.removesuffix("*")
                for file in os.listdir(src_dir):
                    src_file = os.path.join(src_dir, file)
                    dst_file = os.path.join(dst, file)
                    if not os.path.isdir(src_file):
                        shutil.copyfile(src_file, dst_file)
                        os.remove(src_file)
                    else:
                        shutil.copytree(src_file, dst_file, dirs_exist_ok=True)
                        shutil.rmtree(src_file)
                dst_file = dst + "*"
            case "tarball":
                assert path_is_directory(dst), f"Target {dst} must be a directory for tarball relocation"
                cmd = ["tar", "--zstd", "-xf", src, "-C", dst]
                dst_file = dst + "*"
                subprocess.run(cmd, check=True)
                os.remove(src)
            case "normal":
                target_is_dir = path_is_directory(dst)
                if target_is_dir:
                    dst_file = os.path.join(dst, os.path.basename(src.removesuffix("/")))
                else:
                    dst_file = dst
                shutil.move(src, dst_file)
        click.echo(f"Relocated {item.from_} to {dst_file}.")

def file_md5(file_path: str) -> str:
    """Calculate the MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def concat_file(file_path: str, part_files: list[str], *, delete_cache: bool = False) -> None:
    """Concatenate part files into a single file."""
    with open(file_path, "wb") as outfile:
        for part_file in part_files:
            with open(part_file, "rb") as infile:
                outfile.write(infile.read())
            if delete_cache:
                os.remove(part_file)

def extract_tarball(tarball_path: str, extract_to: str) -> None:
    """Extract a tarball to a specified directory."""
    subprocess.run(["tar", "--zstd", "-xvf", tarball_path, "-C", extract_to], check=True)
    os.remove(tarball_path)


@dataclass
class PartFileInfo:
    size: int
    name: str
    download_url: str
    md5: str | None

def download_data(ignore_cache: bool, debug: bool, record_id: str | None, only_relocate: bool=False):
    if record_id is None:
        record_id = click.prompt("Please enter the Zenodo record ID: ", type=str)
    UNZIP_DIR = os.path.realpath(os.path.join(TMP_UNZIP_DIR, "data"))
    if not only_relocate:
        if not debug:
            FILE_LIST_URL = f"{ZENODO_API_BASE}/records/{record_id}"
            response = requests.get(FILE_LIST_URL)
            file_list = response.json()["files"]
            metadata_url = None
            for file in file_list:
                if file["key"] == "data_metadata.json":
                    metadata_url = file["links"]["self"]

            assert metadata_url is not None, "Metadata file not found"
            response = requests.get(metadata_url)
            metadata = response.json()
            part_files = metadata["part_files"]

            part_file_info = []
            for part_file in part_files:
                for file in file_list:
                    if part_file == file["key"]:
                        part_file_info.append(PartFileInfo(
                            size=file["size"],
                            name=file["key"],
                            download_url=file["links"]["self"],
                            md5=file["checksum"].removeprefix("md5:") if file["checksum"].startswith("md5:") else None
                        ))

            if not os.path.exists(CACHE_DIR):
                os.makedirs(CACHE_DIR)

            click.echo(f"Downloading {len(part_file_info)} data files...")

            BLOCK_SIZE = 8192
            cached_files = set(os.path.realpath(os.path.join(CACHE_DIR, f))  for f in os.listdir(CACHE_DIR))
            download_files = []
            for info in tqdm(part_file_info, desc="Downloading files", position=0):
                download_to = os.path.realpath(os.path.join(CACHE_DIR, info.name))
                if not ignore_cache and download_to in cached_files:
                    md5 = file_md5(download_to)
                    if info.md5 is None:
                        click.echo(f"WARNING: File {info.name} already exists but the online information doesn't contain an MD5 checksum. Checksum validation skipped.")
                        continue
                    elif md5 == info.md5:
                        # click.echo(f"File {info.name} already exists and is valid. Skipping download.")
                        download_files.append(download_to)
                        continue
                    else:
                        # click.echo(f"MD5 mismatch: {md5}!={info.md5}. Re-downloading...")
                        pass
                with open(download_to, "wb") as f, tqdm(total=info.size, unit='B', unit_scale=True, desc=info.name, position=1, leave=False) as pbar:
                    response = requests.get(info.download_url, stream=True)
                    for chunk in response.iter_content(chunk_size=BLOCK_SIZE):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
                download_files.append(download_to)
                md5 = file_md5(download_to)
                if info.md5 is None:
                    click.echo(f"WARNING: File {info.name} downloaded but the online information doesn't contain an MD5 checksum. Checksum validation skipped.")
                elif md5 != info.md5:
                    click.echo(f"MD5 mismatch for downloaded {info.name}: expected {info.md5}, got {md5}. Please try again.")
                    raise ValueError(f"MD5 mismatch for downloaded {info.name}: expected {info.md5}, got {md5}")

        else:
            click.echo("Debug mode: using cached files only.")
            download_files = [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR) if f[:-2].endswith(".tar.zst.part")]
            download_files.sort()

        if not os.path.exists(TMP_UNZIP_DIR):
            os.makedirs(TMP_UNZIP_DIR)
        concat_to = os.path.realpath(os.path.join(TMP_UNZIP_DIR, "data.tar.zst"))
        click.echo(f"Concatenating {len(download_files)} part files into {concat_to}...")
        concat_file(concat_to, download_files)

        if not os.path.exists(UNZIP_DIR):
            os.makedirs(UNZIP_DIR)
        click.echo(f"Extracting {concat_to} to {UNZIP_DIR}...")
        extract_tarball(concat_to, UNZIP_DIR)
        click.echo("Download and extraction completed.")
        click.echo("Relocating files...")
    relocate(UNZIP_DIR)
    click.echo("Done!")
