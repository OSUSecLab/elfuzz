import json
import os
import requests
from dataclasses import dataclass
import hashlib
from tqdm import tqdm
import click
import subprocess
import shutil

PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
CLI_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "."))

FIGSHARE_API_BASE = "https://api.figshare.com/v2"
ARTICLE_ID = "29177162"
CACHE_DIR = "/tmp/elfuzz_data_cache"
TMP_UNZIP_DIR = "/tmp/unzip"

@dataclass
class RelocateTo:
    from_: str
    to: str
    is_dir: bool

def load_relocate_info() -> list[RelocateTo]:
    with open(os.path.join(CLI_DIR, "relocate.json")) as f:
        return [RelocateTo(from_=item["from"], to=item["to"], is_dir=item["from"].endswith("/")) for item in json.load(f)]

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
            for file in files:
                shutil.move(os.path.join(src, file), os.path.join(dst, file))
        else:
            shutil.move(src, dst)

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
    subprocess.run(["tar", "--zstd", "-xv", tarball_path, "-C", extract_to], check=True)
    os.remove(tarball_path)


@dataclass
class PartFileInfo:
    size: int
    name: str
    download_url: str
    md5: str

def download_data(ignore_cache: bool):
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
    concat_file(concat_to, download_files, delete_cache=True)

    unzip_dir = os.path.realpath(os.path.join(PROJECT_ROOT, "data"))
    if not os.path.exists(unzip_dir):
        os.makedirs(unzip_dir)
    click.echo(f"Extracting {concat_to} to {unzip_dir}...")
    extract_tarball(concat_to, unzip_dir)
    click.echo("Download and extraction completed.")
    click.echo("Relocating files...")
    relocate(unzip_dir)
    click.echo("Done!")
