"""Update a challenge in challenges.yaml.

    .venv/bin/python tools/set_entry.py llm02 challenges/llm02_x/app.py "flag{...}" "Summary."
    .venv/bin/python tools/set_entry.py --level2 llm03 "Title" "flag{...}" "Summary."
"""
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def set_entry(cid, entry, flag, summary):
    p = ROOT / "challenges.yaml"
    s = p.read_text()
    block = re.search(rf"  - id: {cid}\n(?:    .*\n)+", s).group(0)
    nb = re.sub(r"    entry: .*\n", f"    entry: {entry}\n", block)
    nb = re.sub(r"    flag_sha256: .*\n", f"    flag_sha256: {hashlib.sha256(flag.encode()).hexdigest()}\n", nb)
    nb = re.sub(r"    summary: .*\n", f"    summary: {summary}\n", nb)
    p.write_text(s.replace(block, nb))




def set_level2(cid, title, flag, summary):
    """Add or replace the optional level2 block of a challenge."""
    p = ROOT / "challenges.yaml"
    s = p.read_text()
    block = re.search(rf"  - id: {cid}\n(?:    .*\n)+", s).group(0)
    nb = re.sub(r"    level2:\n(?:      .*\n)+", "", block)
    nb += (f"    level2:\n      title: {title}\n"
           f"      flag_sha256: {hashlib.sha256(flag.encode()).hexdigest()}\n"
           f"      summary: {summary}\n")
    p.write_text(s.replace(block, nb))


if __name__ == "__main__":
    if sys.argv[1] == "--level2":
        set_level2(*sys.argv[2:6])
    else:
        set_entry(*sys.argv[1:5])
