import json
import os
import requests
from dataclasses import dataclass
import hashlib
from tqdm import tqdm
import click
import subprocess
import shutil
from typing import Callable

from common import PROJECT_ROOT, CLI_DIR

FIGSHARE_API_BASE = "https://api.figshare.com/v2"
ARTICLE_ID = "29177162"
CACHE_DIR = "/tmp/cache"
TMP_UNZIP_DIR = "/tmp/unzip"

RELOCATE_HOOK = Callable[[str], None]

@dataclass
class RelocateTo:
    from_: str
    to: str
    is_dir: bool
    hook: RELOCATE_HOOK | None
    is_tarball: bool

def is_dir(path: str) -> bool:
    return os.path.isdir(path)

def load_relocate_info() -> list[RelocateTo]:
    with open(os.path.join(CLI_DIR, "relocate.json")) as f:
        hook = None
        result = []
        for item in json.load(f):
            from_ = item["from"]
            to = item["to"]
            is_dir = item.get("is_dir", False)
            if "is_tarball" in item:
                is_tarball = item["is_tarball"]
            else:
                is_tarball = False
            hook = None
            if "hook" in item:
                hook = globals().get(item["hook"], None)
                assert hook is not None, f"Hook {item['hook']} not found"
            result.append(RelocateTo(from_=from_, to=to, is_dir=is_dir, hook=hook, is_tarball=is_tarball))
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
        if item.is_dir and not os.path.exists(dst):
            os.makedirs(dst)
        elif not item.is_dir:
            target_dir = os.path.dirname(dst)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

        if item.is_dir:
            files = os.listdir(src)
            if not os.path.exists(src):
                click.echo(f"WARNING: Path {src} does not exist. Skipping.")
            else:
                for file in files:
                    shutil.move(os.path.join(src, file), os.path.join(dst, file))
                if item.hook is not None:
                    item.hook(dst)
                click.echo(f"Relocated {item.from_} to {item.to}.")
        else:
            if not os.path.exists(src):
                click.echo(f"WARNING: Path {src} does not exist. Skipping.")
            else:
                target_is_dir = is_dir(dst)
                if not item.is_tarball:
                    if target_is_dir:
                        if not os.path.exists(dst):
                            os.makedirs(dst)
                        
                        shutil.move(src, os.path.join(dst, os.path.basename(src)))
                    else:
                        shutil.move(src, dst)
                else:
                    assert target_is_dir, "Target directory must be a directory for tarball relocation"
                    if not os.path.exists(dst):
                        os.makedirs(dst)
                    cmd = ["tar", "--zstd", "-xf", src, "-C", dst]
                    subprocess.run(cmd, check=True)
                    os.remove(src)
                if item.hook is not None:
                    item.hook(dst)
                click.echo(f"Relocated {item.from_} to {item.to}.")

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
    md5: str

def download_data(ignore_cache: bool, only_relocate: bool=False):
    UNZIP_DIR = os.path.realpath(os.path.join(TMP_UNZIP_DIR, "data"))
    if not only_relocate:
        FILE_LIST_URL = f"{FIGSHARE_API_BASE}/articles/{ARTICLE_ID}/files?page_size=100"
        response = requests.get(FILE_LIST_URL)
        file_list = response.json()
        metadata_url = None
        for file in file_list:
            if file["name"] == "data_metadata.json":
                metadata_url = file["download_url"]

        assert metadata_url is not None, "Metadata file not found"
        response = requests.get(metadata_url)
        metadata = response.json()
        part_files = metadata["part_files"]

        part_file_info = []
        for part_file in part_files:
            for file in file_list:
                if part_file == file["name"]:
                    part_file_info.append(PartFileInfo(
                        size=file["size"],
                        name=file["name"],
                        download_url=file["download_url"],
                        md5=file["computed_md5"]
                    ))

        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)

        click.echo(f"Downloading {len(part_file_info)} data files...")

        BLOCK_SIZE = 8192
        cached_files = set(os.path.realpath(os.path.join(CACHE_DIR, f))  for f in os.listdir(CACHE_DIR))
        download_files = []
        for info in part_file_info:
            download_to = os.path.realpath(os.path.join(CACHE_DIR, info.name))
            if not ignore_cache and download_to in cached_files:
                md5 = file_md5(download_to)
                if md5 == info.md5:
                    click.echo(f"File {info.name} already exists and is valid. Skipping download.")
                    download_files.append(download_to)
                    continue
                else:
                    click.echo(f"MD5 mismatch: {md5}!={info.md5}. Re-downloading...")
            with open(download_to, "wb") as f, tqdm(total=info.size, unit='B', unit_scale=True, desc=info.name) as pbar:
                response = requests.get(info.download_url, stream=True)
                for chunk in response.iter_content(chunk_size=BLOCK_SIZE):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            download_files.append(download_to)
            md5 = file_md5(download_to)
            assert md5 == info.md5, f"MD5 mismatch for {info.name}: expected {info.md5}, got {md5}"

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
