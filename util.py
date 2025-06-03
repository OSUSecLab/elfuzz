import subprocess
from typing import Union

def get_config(key: str) -> Union[str, list[str]]:
    cmd = [
        './elmconfig.py',
        'get',
        key
    ]
    p = subprocess.run(cmd, capture_output=True, check=True)
    r = p.stdout.decode().strip()
    if r.count(' ') > 0:
        return r.split(' ')
    else:
        return r
