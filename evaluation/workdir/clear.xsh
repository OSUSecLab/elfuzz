#!/usr/bin/env xonsh

import os.path
import shutil
import os

cwd = os.path.abspath(os.path.dirname(__file__))

files_or_dirs = os.listdir(cwd)

for f_or_d in files_or_dirs:
    full_p = os.path.join(cwd, f_or_d)
    if os.path.isdir(full_p):
        continue
    else:
        assert os.path.isfile(full_p)
        if (full_p.endswith('.xsh') or 
            full_p.endswith('.py') or
            full_p.endswith('.toml')):
            continue
        os.remove(full_p)
