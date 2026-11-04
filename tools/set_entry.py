"""Update one challenge's entry, flag hash and summary in challenges.yaml.

    .venv/bin/python tools/set_entry.py llm02 challenges/llm02_x/app.py "flag{...}" "Summary text."
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


if __name__ == "__main__":
    set_entry(*sys.argv[1:5])
