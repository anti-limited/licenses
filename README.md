# Licenses

License texts used across counter.ltd projects. Counter-limitation licenses —
built to protect user agency, education, and openness while blocking
corporate profit extraction.

## Index

| File | License | Use |
|------|---------|-----|
| [CLL.md](CLL.md) | Counter-Limitation License (CLL) v1.2 | General-purpose. Drop into any project. |
| [CFL.md](CFL.md) | Counter-Limitation Fork License (CFL) v1.1 | Forked/derived projects with an upstream license. |
| [ACL.md](ACL.md) | Arcadia Community License (ACL) v1.8 | Arcadia project only. |

## Descriptions

### [CLL.md](CLL.md) — Counter-Limitation License v1.2

General copy-paste license for any counter.ltd or anti.ltd project. Project-agnostic
derivative of the ACL — same values, no Arcadia-specific wording.

Grants free use to individuals, learners, educators, researchers, artists,
and small communities. Restricts: Large Corporations (over $10M revenue or
over 100 staff), profit extraction, sale of derivatives, and
harmful/manipulative use. Adds user-protection clauses — data portability, telemetry consent,
end-user modification right, decision transparency, anti-AI-training.
Authorized commercial revenue must be directed to charity. Governed by
laws of England and Wales.

### [CFL.md](CFL.md) — Counter-Limitation Fork License v1.1

For projects forked from or built on third-party software that carries
its own license. Same values and conditions as the CLL, plus fork-specific
terms: the upstream license is preserved verbatim in `ORIGINAL_LICENSE.md`,
upstream notices and attribution are kept intact, and — where the two
conflict over the unmodified upstream code — the upstream license wins.
The CFL governs the fork modifications and the combined work.

Use only where the upstream license permits added terms on derivative/
combined works (MIT, BSD, Apache-2.0, ISC, etc.). Do not apply it over
strong-copyleft upstreams (GPL family).

### [ACL.md](ACL.md) — Arcadia Community License v1.8

Original license. Specific to the Arcadia project — references Arcadia's
runtime, module system, and shell. CLL is the generalized version of this
license; use CLL for new projects, ACL for Arcadia itself.

## Tooling — `update_license.py`

Python script (stdlib only, no deps) to install/refresh a license in any
repo and manage its Excluded Entity Restriction Addendum. Run it from a
license root with a repo path, or from inside the target repo (path
defaults to the current directory).

### `refresh` — install or update the license

Pulls the standard license text from the canonical repo and writes it to
the target's `LICENSE.md`. Any project-specific addenda already present
(e.g. an Excluded Entity Restriction Addendum) are detected and preserved
verbatim below the refreshed text.

```sh
python3 update_license.py refresh --license CLL /path/to/repo
cd /path/to/repo && python3 /path/to/update_license.py refresh -l CFL
```

`--license` / `-l` is required: `CLL`, `ACL`, or `CFL`.

### `exclude` — manage the Excluded Entity Restriction Addendum

Add, remove, list, or wipe excluded entities. Requires a `LICENSE.md` to
exist (run `refresh` first).

```sh
python3 update_license.py exclude --add "Corgi s.r.o." /path/to/repo
python3 update_license.py exclude --remove "Corgi s.r.o." /path/to/repo
python3 update_license.py exclude --list /path/to/repo
python3 update_license.py exclude --wipe /path/to/repo
```

- `--add` creates the addendum if absent; duplicate names are ignored.
- `--remove` drops one entity; removing the last one deletes the whole
  addendum.
- `--wipe` removes the entire addendum.
- `--list` prints the current excluded entities.
- Repo path is optional and defaults to the current directory.
