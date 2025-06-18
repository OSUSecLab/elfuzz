import os
import re

PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
CLI_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "."))
USER = "appuser"
UID = 1000

def trim_indent(s: str, *, delimiter: str = " ") -> str:
    ended_with_newline = s.endswith("\n")
    lines = s.removesuffix("\n").split("\n")
    new_lines = []
    for l in lines:
        m = re.match(r"^(\s*|).*$", l)
        if m:
            to_trim = len(m.group(1))
            new_lines.append(l[to_trim+1:])
        else:
            new_lines.append(l)
    if len(new_lines) > 0:
        if not new_lines[0].strip():
            new_lines.pop(0)
    if len(new_lines) > 1:
        if not new_lines[-1].strip():
            new_lines.pop(-1)
    return delimiter.join(new_lines) + ("\n" if ended_with_newline else "")

