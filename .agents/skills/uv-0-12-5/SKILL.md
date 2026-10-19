---
name: uv-0-12-5
description: "Manages Python projects, scripts, and Python itself with uv 0.12.5, the fast Rust-based package manager. Use when creating Python projects or scripts, adding or removing dependencies, locking or exporting dependencies, syncing environments, running commands or tools with uv run or uvx, installing Python versions, or building and publishing packages. Covers the full uv CLI and dependency declaration via pyproject.toml, dependency-groups, tool.uv.sources, and PEP 723 inline script metadata."
license: MIT OR Apache-2.0
compatibility: Requires the uv 0.12.5 CLI on PATH
metadata:
  tags:
    - packaging
    - python
    - dependency-management
---

# uv 0.12.5

## Overview

uv 0.12.5 is a fast, Rust-based package manager that unifies Python workflows in a single binary. It creates and manages virtual environments, resolves and locks dependencies (`uv.lock`), and can download and manage CPython and PyPy builds itself — no separate pip, venv, or pyenv needed.

Interfaces, usable independently or together:

- **Projects** — `pyproject.toml` + `uv.lock` + `.venv`, managed with `uv init`, `uv add`, `uv remove`, `uv lock`, `uv sync`, `uv run`, `uv build`, `uv publish`
- **Scripts** — standalone `.py` files with PEP 723 inline dependency metadata, run via `uv run`, managed with `uv add --script`
- **Tools** — one-off CLI tools via `uvx` (alias of `uv tool run`), user-wide tools via `uv tool install`
- **Python versions** — `uv python install/list/find/pin/uninstall`
- **pip interface** — `uv pip install/compile/sync` and `uv venv` for legacy or manual environment workflows

## Usage

Typical project workflow:

```bash
uv init hello-world && cd hello-world
uv add requests              # adds to project.dependencies, locks, syncs .venv
uv run python main.py        # verifies lock + env are current before running
uv lock --upgrade-package requests   # upgrade one locked package, keep the rest
uv export --format requirements.txt -o requirements.txt
```

PEP 723 scripts (no `pyproject.toml` needed):

```bash
uv init --script example.py --python 3.12
uv add --script example.py 'requests<3'
uv run example.py            # environment created from the inline metadata block
```

Tools and Python versions:

```bash
uvx ruff check .             # run a tool in a temporary isolated environment
uv tool install ruff         # install a tool user-wide
uv python install 3.12
uv python pin 3.12           # writes .python-version for the project
```

The full command reference with per-command flags is in [01-cli](references/01-cli.md); every way to declare dependencies (fields, sources, extras, groups, indexes, PEP 723, lockfile) is in [02-dependencies](references/02-dependencies.md).

## Gotchas

- **The lockfile does not go stale when new releases appear** — `uv lock` and `uv sync` prefer previously locked versions unless a constraint excludes them. Upgrade explicitly with `uv lock --upgrade` (all) or `uv lock --upgrade-package <pkg>==<ver>`.
- **`uv add` changes the constraint, not the locked version** — `uv add "httpx>0.1.0"` keeps the locked httpx if it still satisfies the new constraint; add `--upgrade-package httpx` to move to the latest allowed version.
- **`uv run` and `uv sync` differ in sync strictness** — `uv sync` is exact by default (removes packages absent from the lockfile); `uv run` is inexact (installs missing packages, keeps extraneous ones). Use `uv run --exact` or `uv sync --inexact` to flip.
- **Do not `uv pip install` into a project** — use `uv add` for project dependencies and `uv run --with <pkg>` or `uvx` for one-offs. `uv pip install` bypasses the lockfile and desyncs the environment from `uv.lock`.
- **In a project, `uv run <script>` installs the current project first** — pass `--no-project` (before the script name) if the script does not need it. PEP 723 scripts are the opposite case: the inline metadata takes precedence over any surrounding project, so no flag is needed.
- **Extras are not synced by default** — `uv sync --extra <name>` or `--all-extras`; the `dev` group is the only one included by default (toggle with `--no-dev`, `--only-dev`, `--no-default-groups`).
- **`--frozen`, `--locked`, and `--no-sync` do different things** — `--frozen` uses `uv.lock` as-is without checking it is up-to-date; `--locked` asserts the lockfile is up-to-date and errors if not; `--no-sync` skips environment syncing altogether (the lockfile may still be re-locked).
- **`tool.uv.sources` is honored only by uv** — git/path/workspace/index overrides are invisible to pip and other tools. Before publishing, verify the project builds with `uv build --no-sources` and `uv lock --no-sources`.
- **`uvx` isolates from the project** — `uvx pytest` runs in a temporary environment where the project is not installed. Use `uv run <tool>` for tools that operate on the project (pytest, mypy, ruff on project code).
- **Configuration precedence is CLI > env vars > project > user > system** — within a directory `uv.toml` wins over `pyproject.toml` (`[tool.uv]`), and arrays from different levels are concatenated (project entries first). `--no-config` disables discovery entirely.
- **`uv.lock` is uv-managed** — commit it, never edit it by hand, and know its format is uv-specific. Export with `uv export` to get `requirements.txt`, `pylock.toml` (PEP 751), or CycloneDX SBOM output.
- **Group exclusions always beat inclusions** — `uv sync --no-group foo --group foo` installs nothing from `foo`.
- **`uv venv` creates an empty environment** — it does not install the project or its dependencies; run `uv sync` (or `uv run`) to populate it.
- **Workspace members are not dependencies by default** — a member under `[tool.uv.workspace]` only becomes a dependency when declared with `dependencies = ["<member>"]` plus `tool.uv.sources` entry `{ workspace = true }`. `uv init` inside an existing package does this automatically.
- **`.python-version` and `requires-python` do different jobs** — the file pins the interpreter used for the environment (write it with `uv python pin`); `requires-python` constrains the resolution range.
- **`--index` adds, `--default-index` replaces** — `--index` adds an index alongside PyPI; `--default-index` replaces PyPI as the fallback. The default index is always lowest priority regardless of list position. `-i/--index-url` and `--extra-index-url` are deprecated aliases.
- **When a PEP 723 script declares `requires-python`, uv downloads that interpreter if missing** — the inline `[tool.uv]` section in the metadata block (e.g., `exclude-newer`) is respected for reproducibility.

## References

- [01-cli](references/01-cli.md) — Complete CLI command reference for uv 0.12.5, global options, and shared option groups
- [02-dependencies](references/02-dependencies.md) — Declaration of dependencies, pyproject.toml fields, PEP 508 specifiers, tool.uv.sources, extras, dependency groups, indexes, PEP 723 scripts, lockfile
