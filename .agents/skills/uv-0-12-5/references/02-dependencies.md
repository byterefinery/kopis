# uv 0.12.5 — Declaration of Dependencies

- [The dependency fields](#the-dependency-fields)
- [Editing dependencies with uv add and uv remove](#editing-dependencies-with-uv-add-and-uv-remove)
- [Dependency specifiers (PEP 508)](#dependency-specifiers-pep-508)
- [Platform-specific dependencies](#platform-specific-dependencies)
- [Dependency sources (tool.uv.sources)](#dependency-sources-tooluvsources)
- [Optional dependencies (extras)](#optional-dependencies-extras)
- [Development dependencies and groups](#development-dependencies-and-groups)
- [Build dependencies](#build-dependencies)
- [Editable and virtual dependencies](#editable-and-virtual-dependencies)
- [Package indexes](#package-indexes)
- [PEP 723 scripts](#pep-723-scripts)
- [The lockfile](#the-lockfile)
- [Workspaces](#workspaces)

## The dependency fields

A project's dependencies live in `pyproject.toml`. Four declaration fields, plus build metadata:

| Field | Audience | Notes |
|---|---|---|
| `[project] dependencies` | Runtime, published | PEP 621 standard; included in the wheel metadata |
| `[project.optional-dependencies]` | Runtime, opt-in | "Extras", requested as `pkg[extra]` |
| `[dependency-groups]` | Development, local-only | PEP 735; never published; `dev` group included by default |
| `[tool.uv.sources]` | Development, uv-only | Alternative sources (git, path, url, index, workspace) for the above |
| `[build-system] requires` | Build time | PEP 518; deps needed to build the project itself |

`project.dependencies` and `project.optional-dependencies` work even for unpublished projects; `dependency-groups` is newer and may not be supported by all third-party tools.

## Editing dependencies with uv add and uv remove

Prefer the CLI over hand-editing — it re-locks and syncs, and rewrites sources correctly:

```bash
uv add httpx                      # -> "httpx>=0.27.2" in project.dependencies (lower bound by default)
uv add "httpx>=0.20"              # explicit constraint
uv add "httpx" --bounds major     # -> "httpx>=0.27.2,<1"
uv add "httpx" --bounds exact     # -> "httpx==0.27.2"
uv add "httpx>9999"               # -> resolution error, nothing written
uv add "httpx @ git+https://github.com/encode/httpx"   # rewrites into tool.uv.sources
uv add "jax; sys_platform == 'linux'"                  # marker preserved in the entry
uv add -r requirements.txt -c constraints.txt          # import from files
uv add --dev pytest               # -> [dependency-groups] dev
uv add --group lint ruff          # -> [dependency-groups] lint
uv add --optional network httpx   # -> [project.optional-dependencies] network
uv remove httpx                   # removes entry + orphaned source
uv add "httpx>0.1.0" --upgrade-package httpx   # change constraint AND bump locked version
```

Semantics to keep in mind:

- `uv add` on an existing dependency **updates the constraint only**. The locked version changes only if the new constraint excludes it; force it with `--upgrade-package <name>`.
- Non-registry requirements (git, url, path, index) are split: the plain name goes in `dependencies`, the source goes in `tool.uv.sources`. `--raw` suppresses this.
- Changing the source (e.g., `uv add "httpx @ ../httpx"`) updates the sources table; reverting back to a registry dependency restores it.

## Dependency specifiers (PEP 508)

Order: name, extras, version specifier, environment marker.

```toml
dependencies = [
  "tqdm >=4.66.2,<5",                                    # range
  "torch ==2.2.2",                                       # exact
  "transformers[torch] >=4.39.3,<5",                     # with extra
  "importlib_metadata >=7.1.0,<8; python_version < '3.10'",  # with marker
]
```

Version specifier rules:

- Comma-separated, conjoined (`foo >=1.2.3,<2,!=1.4.0`).
- `~=` is the compatible release: `foo ~=1.2` ≡ `>=1.2,<2`; `foo ~=1.2.3` ≡ `>=1.2.3,<1.3`.
- `==` supports a trailing `*`: `foo ==2.1.*` accepts the whole 2.1 series.
- Versions are zero-padded: `foo ==2` matches `2.0.0`.
- Extras are comma-separated in brackets between name and version: `pandas[excel,plot] ==2.2`.
- Markers combine with `and`, `or`, parentheses; **quote versions inside markers** (`python_version < '3.10'`) but never outside them (`tqdm >=4,<5`).
- Common markers: `sys_platform`, `platform_system`, `os_name`, `python_version`, `implementation_name`.

## Platform-specific dependencies

Attach an environment marker to the dependency entry:

```bash
uv add "jax; sys_platform == 'linux'"
uv add "numpy; python_version >= '3.11'"
```

## Dependency sources (tool.uv.sources)

`[tool.uv.sources]` extends the standard fields with non-registry sources. Sources are **uv-only** — pip, poetry, and other tools see only the standard `dependencies` entries. Verify publishability with `uv lock --no-sources` / `uv build --no-sources`.

Five source kinds, keyed by dependency name:

```toml
[tool.uv.sources]
# Index — pin a package to a specific index
torch = { index = "pytorch" }

# Git — with optional tag / branch / rev / subdirectory / lfs
httpx = { git = "https://github.com/encode/httpx", tag = "0.27.0" }

# URL — direct wheel or sdist download
httpx = { url = "https://files.pythonhosted.org/.../httpx-0.27.0.tar.gz" }

# Path — local wheel, sdist, or project directory (editable via --editable)
foo = { path = "./packages/foo" }
bar = { path = "../projects/bar", editable = true }

# Workspace member (always editable)
bird-feeder = { workspace = true }
```

CLI equivalents: `uv add git+https://… --tag X --branch Y --rev Z --lfs`, `uv add --index pytorch=https://download.pytorch.org/whl/cpu torch` (writes both the `[[tool.uv.index]]` entry and the source), `uv add ./foo-0.1.0-py3-none-any.whl`, `uv add --editable ../bar/`.

**Platform-specific sources** — add `marker` to the source; the package is still installed everywhere, only the origin varies:

```toml
[tool.uv.sources]
httpx = { git = "https://github.com/encode/httpx", tag = "0.27.2", marker = "sys_platform == 'darwin'" }
```

**Multiple sources** — a list, disambiguated by `marker` (also works with per-`extra` sources, using the `extra` key):

```toml
[tool.uv.sources]
torch = [
  { index = "torch-cpu", marker = "platform_system == 'Darwin'" },
  { index = "torch-gpu", marker = "platform_system == 'Linux'" },
]
```

**Disabling** — `--no-sources` (global) or `--no-sources-package <name>` ignore the table for one resolution; this also disables workspace-member discovery for those names.

## Optional dependencies (extras)

```toml
[project.optional-dependencies]
plot = ["matplotlib>=3.6.3"]
excel = ["openpyxl>=3.1.0", "xlsxwriter>=3.0.5"]
```

- Requested at install time as `pkg[plot]` / `uv sync --extra plot` / `--all-extras`.
- Managed with `uv add --optional <extra> <pkg>` / `uv remove --optional <extra> <pkg>`.
- Extras can carry their own sources (including per-extra index sources via the `extra` key in `tool.uv.sources`).
- Extras are **not synced by default** — an environment only gets them when requested.
- Conflicting extras (two extras that cannot be installed together) break resolution unless declared in `[tool.uv] conflicts`.

## Development dependencies and groups

Development dependencies are local-only: never published, never installed into a consuming environment. Declared under `[dependency-groups]` (PEP 735):

```bash
uv add --dev pytest        # -> [dependency-groups] dev
uv add --group lint ruff   # -> [dependency-groups] lint
```

```toml
[dependency-groups]
dev = [{include-group = "lint"}, {include-group = "test"}]   # groups can nest
lint = ["ruff"]
test = ["pytest"]
```

Key semantics:

- The `dev` group is special-cased: synced by default, toggled with `--dev`/`--no-dev`/`--only-dev` (equivalent to `--group dev` variants). All other groups are opt-in (`--group <name>`, `--only-group <name>`, `--all-groups`, `--no-group <name>`).
- Default groups are configurable: `[tool.uv] default-groups = ["dev", "foo"]` or `"all"`; `--no-default-groups` opts out.
- uv resolves **all groups together** and requires them to be mutually compatible; conflicting groups must be declared under `[tool.uv] conflicts`.
- A group can declare its own `[tool.uv.dependency-groups] <group> = { requires-python = ">=3.12" }` when it needs a different Python range than the project.
- Legacy `tool.uv.dev-dependencies` still works (combined into `dependency-groups.dev`), but is deprecated; `uv add --dev` reuses an existing `dev-dependencies` section if present.

## Build dependencies

Declared under `[build-system]` (PEP 518); used only to build the project:

```toml
[build-system]
requires = ["uv_build>=0.12.5,<0.13"]
build-backend = "uv_build"
```

- Without a `[build-system]` table, the project is not installed during `uv sync` (it is "virtual" in effect), though `uv build` falls back to legacy setuptools.
- `build-system.requires` also respects `tool.uv.sources` (e.g., a local setuptools for builds); publish with `uv build --no-sources` to test the published build.

## Editable and virtual dependencies

**Editable** — installs a link (`.pth`) to the source instead of copying built files; source changes are immediately visible. uv uses editables for the project and workspace members by default; add others with `uv add --editable <dir>` (or `editable = true` on a path source). Opt out per-sync with `--no-editable`.

**Virtual** — a dependency whose *dependencies* are installed but the package itself is not. Set `package = false` in the dependency's own `tool.uv` settings (or `package = false`/`true` on the source to override per-edge). Useful for "library of scripts" members without a build system.

## Package indexes

The default index is PyPI (`https://pypi.org/simple`). Additional indexes are declared in `[[tool.uv.index]]`:

```toml
[[tool.uv.index]]
name = "pytorch"                                   # optional; [A-Za-z0-9._-]
url = "https://download.pytorch.org/whl/cpu"
default = true          # replace PyPI as the fallback (else use --default-index)
explicit = true         # only used by packages pinned via tool.uv.sources
publish-url = "https://test.pypi.org/legacy/"      # for uv publish --index <name>
```

- Indexes are consulted **in definition order**; CLI indexes beat config-file indexes; the default index is always last.
- Pin a package to an index with the `index` source kind (`torch = { index = "pytorch" }`); unpinned packages may resolve from any index.
- Multiple indexes: `--index-strategy first-index` (default, each package resolves from the first index that has it) or `unsafe-first-match` / `unsafe-best-match` (search across indexes).
- CLI: `--index <url|name=...>` adds, `--default-index <url>` replaces PyPI; env vars `UV_INDEX`, `UV_DEFAULT_INDEX`.
- Auth: basic auth in the URL (`https://user:token@host/...`), `[tool.uv.index]` `auth` table (token, keyring), or `uv auth login`. Flat repositories (no Simple API) via `--find-links`.
- Relative package-index paths in PEP 723 scripts resolve against the script directory (0.12.5).

## PEP 723 scripts

Standalone scripts declare dependencies inline, after the docstring position, in a TOML block:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests<3", "rich"]
# [[tool.uv.index]]
# url = "https://example.com/simple"
# [tool.uv]
# exclude-newer = "2023-10-16T00:00:00Z"
# ///

import requests
```

Rules and tooling:

- `dependencies` must be present even when empty; `requires-python` selects/downloads the interpreter.
- Manage via CLI: `uv init --script example.py --python 3.12`, `uv add --script example.py 'requests<3'`, `uv remove --script example.py rich` — uv rewrites the block in place.
- `uv run example.py` builds an environment from the metadata; `uv run --script <file>` is explicit. In a project, an inline metadata block **takes precedence over the project** (no `--no-project` needed).
- Locking is opt-in: `uv lock --script example.py` writes `example.py.lock`; `run`/`add`/`export`/`tree --script` then reuse it.
- `[tool.uv] exclude-newer` (RFC 3339) in the block pins resolution to a date for reproducibility.
- Shebang for direct execution: `#!/usr/bin/env -S uv run --script` + `chmod +x`.
- One-off dependencies without editing the file: `uv run --with 'rich>12,<13' example.py`.

## The lockfile

`uv.lock` (TOML, uv-specific format) sits next to `pyproject.toml` and is a **universal** lockfile — it records resolutions for all supported platforms/Python versions, so one file serves every environment.

- Auto-created/refreshed by `uv run`, `uv sync`, and other project commands; explicit with `uv lock`.
- **Staleness**: the lockfile is outdated only when `pyproject.toml` metadata changes in a way that excludes a locked version (new deps, changed constraints, changed sources). New upstream releases do *not* invalidate it. Check with `uv lock --check`.
- **Upgrades**: `uv lock --upgrade` (all), `uv lock --upgrade-package <pkg>` (one, latest allowed), `uv lock --upgrade-package <pkg>==<ver>` (one, exact). Same flags on `uv sync`/`uv run` update lock and env together. Git sources pin to the locked commit until upgraded.
- **Never edit by hand.** Commit it to VCS.
- **Export**: `uv export --format requirements.txt|pylock.toml|cyclonedx1.5` for other tools and SBOM workflows (`pylock.toml` is PEP 751; `uv pip sync`/`uv pip install -r` can consume it).

## Workspaces

A workspace is a set of packages (members) managed under one lockfile, rooted at a `pyproject.toml` with:

```toml
[tool.uv.workspace]
members = ["packages/*"]     # globs; each must contain a pyproject.toml
exclude = ["packages/seeds"] # optional
```

- The root is itself a member. `uv lock` covers the whole workspace; `uv run` / `uv sync` default to the root but accept `--package <member>`.
- Cross-member dependencies are declared normally plus `{ workspace = true }` in `tool.uv.sources`; members are editable by default.
- `uv init` inside a package directory auto-creates/extends the workspace; `uv init --no-workspace` opts out.
- Workspace configuration is read from the root only; members' `[tool.uv]` settings are ignored.
