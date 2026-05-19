#!/usr/bin/env python3
"""Manage a repo's LICENSE.md against the canonical licenses repo.

Two subcommands:

  refresh   Pull the standard license text from
            https://github.com/opensourcevillain/licenses and write it to
            the target repo's LICENSE.md. Project-specific addenda already
            present (e.g. an "Excluded Entity Restriction Addendum") are
            detected and preserved verbatim below the refreshed text.

  exclude   Create, edit, or remove the "Excluded Entity Restriction
            Addendum" in the target repo's LICENSE.md -- add an entity,
            remove an entity, wipe the whole addendum, or list entities.

Target repo is an optional path argument; defaults to the current
directory, so the tool can be run from inside a repo or from anywhere.

Usage:
    python3 update_license.py refresh --license CLL [repo]
    python3 update_license.py exclude --add "Corgi s.r.o." [repo]
    python3 update_license.py exclude --remove "Corgi s.r.o." [repo]
    python3 update_license.py exclude --wipe [repo]
    python3 update_license.py exclude --list [repo]
"""

import argparse
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

RAW_BASE = "https://raw.githubusercontent.com/opensourcevillain/licenses/main"
LICENSES = ("CLL", "ACL", "CFL")
TARGET_NAME = "LICENSE.md"

EER_HEADING = "Excluded Entity Restriction Addendum"

# A heading line that marks the start of a project-specific addendum.
ADDENDUM_HEADING = re.compile(r"^\S.*\baddendum\b\s*$", re.IGNORECASE)
SEPARATOR = re.compile(r"^-{3,}\s*$")

ENTITY_TAIL = (
    "    including its owners, employees, contractors, affiliates,\n"
    "    subsidiaries, successors, and related entities."
)

GRANT_LINE = (
    "Notwithstanding any other provision of this license, no license,\n"
    "permission, authorization, or rights of any kind are granted to:"
)

PROHIBITED_BLOCK = """The above excluded parties are explicitly prohibited from:

- downloading the software;
- accessing the software for operational or commercial purposes;
- using the software in whole or in part;
- executing or running the software;
- copying the software;
- modifying the software;
- creating derivative works;
- distributing or sublicensing the software;
- mirroring or hosting the software;
- incorporating the software into other works, products, or services;
- using any associated assets, branding, documentation, or source code.

Any use by an excluded party shall be considered unauthorized and
outside the scope of this license.

This restriction applies regardless of how the software was obtained."""


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

def fetch_license(name: str) -> str:
    url = f"{RAW_BASE}/{name}.md"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        sys.exit(f"error: fetch {url} failed: HTTP {e.code}")
    except urllib.error.URLError as e:
        sys.exit(f"error: fetch {url} failed: {e.reason}")


# ---------------------------------------------------------------------------
# addenda parsing
# ---------------------------------------------------------------------------

def split_addenda(text: str):
    """Return (standard_text, addenda_text).

    addenda_text is '' when no addendum is found. Detection: the first
    heading line ending in 'Addendum'. A '---' separator and blank lines
    immediately preceding that heading are pulled into the addenda block.
    """
    lines = text.splitlines()
    head_idx = None
    for i, line in enumerate(lines):
        if ADDENDUM_HEADING.match(line):
            head_idx = i
            break
    if head_idx is None:
        return text.rstrip() + "\n", ""

    start = head_idx
    j = head_idx - 1
    while j >= 0 and lines[j].strip() == "":
        j -= 1
    if j >= 0 and SEPARATOR.match(lines[j]):
        start = j
        while start - 1 >= 0 and lines[start - 1].strip() == "":
            start -= 1

    standard = "\n".join(lines[:start]).rstrip() + "\n"
    addenda = "\n".join(lines[start:]).strip() + "\n"
    return standard, addenda


def parse_addenda_blocks(addenda_text: str):
    """Split an addenda region into individual addendum bodies.

    Returns a list of strings, each one addendum (no '---' separator,
    stripped). Order preserved.
    """
    if not addenda_text.strip():
        return []
    blocks, current = [], []
    for line in addenda_text.splitlines():
        if SEPARATOR.match(line):
            if current:
                body = "\n".join(current).strip()
                if body:
                    blocks.append(body)
                current = []
        else:
            current.append(line)
    if current:
        body = "\n".join(current).strip()
        if body:
            blocks.append(body)
    return blocks


def block_heading(block: str) -> str:
    for line in block.splitlines():
        if line.strip():
            return line.strip()
    return ""


def assemble(standard: str, blocks) -> str:
    """Join standard text with addendum blocks under '---' separators."""
    out = standard.rstrip() + "\n"
    for block in blocks:
        out += "\n---\n\n" + block.strip() + "\n"
    return out


# ---------------------------------------------------------------------------
# Excluded Entity Restriction Addendum
# ---------------------------------------------------------------------------

def build_eer_addendum(entities) -> str:
    entity_blocks = "\n\n".join(
        f"    {name}\n{ENTITY_TAIL}" for name in entities
    )
    return (
        f"{EER_HEADING}\n\n"
        f"{GRANT_LINE}\n\n"
        f"{entity_blocks}\n\n"
        f"{PROHIBITED_BLOCK}"
    )


def parse_eer_entities(block: str):
    """Extract entity names from an Excluded Entity Restriction Addendum."""
    lines = block.splitlines()
    names, in_list = [], False
    for line in lines:
        stripped = line.strip()
        if stripped.endswith("are granted to:"):
            in_list = True
            continue
        if not in_list:
            continue
        if stripped.startswith("The above excluded parties"):
            break
        if not line.startswith("    ") or not stripped:
            continue
        # An entity name is the first indented line of a 3-line block;
        # the two boilerplate lines start with "including" / "subsidiaries,".
        if stripped.startswith("including ") or stripped.startswith(
            "subsidiaries,"
        ):
            continue
        names.append(stripped)
    return names


def find_eer(blocks):
    """Return index of the EER addendum block, or None."""
    for i, block in enumerate(blocks):
        if block_heading(block).lower() == EER_HEADING.lower():
            return i
    return None


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def resolve_target(repo_arg: str) -> Path:
    repo = Path(repo_arg).expanduser().resolve()
    if not repo.is_dir():
        sys.exit(f"error: not a directory: {repo}")
    return repo / TARGET_NAME


def cmd_refresh(args) -> None:
    target = resolve_target(args.repo)
    existed = target.exists()
    new_standard = fetch_license(args.license).rstrip() + "\n"

    addenda = ""
    if existed:
        _, addenda = split_addenda(target.read_text(encoding="utf-8"))

    blocks = parse_addenda_blocks(addenda)
    content = assemble(new_standard, blocks)
    target.write_text(content, encoding="utf-8")

    status = "updated" if existed else "created"
    print(f"{status}: {target}")
    print(f"  license: {new_standard.splitlines()[0]}")
    for block in blocks:
        print(f"  preserved addendum: {block_heading(block)}")


def cmd_exclude(args) -> None:
    target = resolve_target(args.repo)
    if not target.exists():
        sys.exit(
            f"error: {target} does not exist -- run 'refresh' first to "
            f"install a license."
        )

    standard, addenda = split_addenda(target.read_text(encoding="utf-8"))
    blocks = parse_addenda_blocks(addenda)
    idx = find_eer(blocks)
    entities = parse_eer_entities(blocks[idx]) if idx is not None else []

    if args.list:
        if entities:
            print(f"excluded entities in {target}:")
            for name in entities:
                print(f"  - {name}")
        else:
            print(f"no Excluded Entity Restriction Addendum in {target}")
        return

    if args.wipe:
        if idx is None:
            print(f"no Excluded Entity Restriction Addendum in {target}")
            return
        del blocks[idx]
        target.write_text(assemble(standard, blocks), encoding="utf-8")
        print(f"wiped Excluded Entity Restriction Addendum from {target}")
        return

    if args.add:
        name = args.add.strip()
        if any(name.lower() == e.lower() for e in entities):
            print(f"already excluded: {name}")
            return
        entities.append(name)
        action = f"added excluded entity: {name}"
    else:  # args.remove
        name = args.remove.strip()
        match = [e for e in entities if e.lower() == name.lower()]
        if not match:
            sys.exit(f"error: not currently excluded: {name}")
        entities = [e for e in entities if e.lower() != name.lower()]
        action = f"removed excluded entity: {name}"

    if entities:
        new_block = build_eer_addendum(entities)
        if idx is None:
            blocks.append(new_block)
        else:
            blocks[idx] = new_block
    elif idx is not None:
        # last entity removed -> drop the empty addendum
        del blocks[idx]
        action += " (addendum now empty, removed)"

    target.write_text(assemble(standard, blocks), encoding="utf-8")
    print(action)
    print(f"  {target}")
    if entities:
        print(f"  excluded now: {', '.join(entities)}")


# ---------------------------------------------------------------------------
# cli
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Manage LICENSE.md against the canonical licenses repo."
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_refresh = sub.add_parser(
        "refresh", help="pull/refresh the standard license text"
    )
    p_refresh.add_argument(
        "-l", "--license", required=True, choices=LICENSES,
        help="which license to pull (CLL, ACL, or CFL)",
    )
    p_refresh.add_argument(
        "repo", nargs="?", default=".",
        help="path to the target repo (default: current directory)",
    )
    p_refresh.set_defaults(func=cmd_refresh)

    p_excl = sub.add_parser(
        "exclude", help="manage the Excluded Entity Restriction Addendum"
    )
    grp = p_excl.add_mutually_exclusive_group(required=True)
    grp.add_argument("--add", metavar="ENTITY", help="add an excluded entity")
    grp.add_argument(
        "--remove", metavar="ENTITY", help="remove an excluded entity"
    )
    grp.add_argument(
        "--wipe", action="store_true",
        help="remove the entire Excluded Entity Restriction Addendum",
    )
    grp.add_argument(
        "--list", action="store_true", help="list excluded entities"
    )
    p_excl.add_argument(
        "repo", nargs="?", default=".",
        help="path to the target repo (default: current directory)",
    )
    p_excl.set_defaults(func=cmd_exclude)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
