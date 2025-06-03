import os.path

CWD = os.path.dirname(__file__)
XDG_DIR = $(xdg-user-dir)
if not os.path.exists(os.path.join(XDG_DIR, '.local', 'share', 'afl.rs')):
    tar --zstd -xf @(CWD)/afl_rs_binaries.tar.zst -C @(XDG_DIR)/.local/share
