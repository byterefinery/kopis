# uv 0.12.5 — CLI Reference

- [Commands](#commands)
- [Global options](#global-options)
- [Shared option groups](#shared-option-groups)
- [Project commands](#project-commands)
- [Python and environments](#python-and-environments)
- [Tools](#tools)
- [pip interface](#pip-interface)
- [Utilities](#utilities)

`uv` prints its command list with no arguments. `uv <command> --help` gives concise usage; `uv help <command>` gives the full prose documentation (the same text as the online CLI reference).

## Commands

| Command | Purpose |
|---|---|
| `uv init [PATH]` | Create a new project or PEP 723 script |
| `uv add` | Add dependencies to a project or script |
| `uv remove` | Remove dependencies from a project or script |
| `uv sync` | Update the project environment from the lockfile |
| `uv lock` | Create or update `uv.lock` |
| `uv export` | Export `uv.lock` to requirements.txt, pylock.toml, or CycloneDX |
| `uv run [COMMAND]` | Run a command or script in the project environment (locks + syncs first) |
| `uv tree` | Display the dependency tree |
| `uv version` | Read or update the project's version |
| `uv audit` | Audit the lockfile for known vulnerabilities (OSV) |
| `uv format` | Format Python code in the project (runs Ruff) |
| `uv check` | Type-check the project (runs the ty checker) |
| `uv build` | Build source and binary distributions into `dist/` |
| `uv publish` | Upload distributions to a package index |
| `uv workspace` | Inspect workspaces (`list`, `dir`, `metadata`) |
| `uv python` | Manage Python versions and installations |
| `uv venv` | Create a virtual environment |
| `uv tool` | Install and run commands provided by Python packages (`uvx` = `uv tool run`) |
| `uv pip` | Manage packages with a pip-compatible interface |
| `uv cache` | Manage uv's cache |
| `uv self` | Manage the uv executable (`update`, `version`) |
| `uv auth` | Manage authentication (`login`, `logout`, `token`, `dir`) |

## Global options

Available on every command:

```text
-q, --quiet...                 Quiet output (repeatable)
-v, --verbose...               Verbose output (repeatable)
--color <auto|always|never>    Control color
--system-certs                 Load TLS certificates from the platform store
--offline                      Disable network access
--allow-insecure-host <HOST>   Allow insecure connections to a host
--no-progress                  Hide progress output
-n, --no-cache                 Do not read/write the cache (temporary dir)
--cache-dir <DIR>              Path to the cache directory
--managed-python               Require uv-managed Python versions
--no-managed-python            Disable uv-managed Python versions
--no-python-downloads          Do not auto-download Python
--directory <DIR>              Change directory before running
--project <DIR>                Discover the project in DIR
--config-file <FILE>           Use a specific uv.toml (overrides discovered config)
--no-config                    Disable configuration discovery
```

Environment variables mirror most flags (`UV_NO_CACHE`, `UV_OFFLINE`, `UV_PYTHON`, `UV_INDEX`, `UV_LOCKED`, `UV_FROZEN`, …).

## Shared option groups

`add`, `sync`, `lock`, `export`, and `run` share these option groups (a subset applies per command):

**Index options**

```text
--index <INDEX>                    Additional index; a URL, a configured index name, or name=URL
--default-index <URL>              Replace PyPI as the default index
-i, --index-url <URL>              Deprecated, use --default-index
--extra-index-url <URL>            Deprecated, use --index
-f, --find-links <LOC>             Flat locations for candidate distributions
--no-index                         Ignore registry indexes entirely
--index-strategy <first-index|unsafe-first-match|unsafe-best-match>
--keyring-provider <disabled|subprocess>
```

**Resolver options**

```text
-U, --upgrade                      Upgrade all packages, ignoring locked versions
-P, --upgrade-package <PKG>        Upgrade one package (repeatable); also accepts pkg==version
--upgrade-group <GROUP>            Upgrade all packages in a dependency group
--resolution <highest|lowest|lowest-direct>
--prerelease <disallow|allow|if-necessary|explicit|if-necessary-or-explicit>
--prerelease-package <PKG>         Prerelease strategy for one package
--fork-strategy <fewest|requires-python>
--exclude-newer <DATE>             Only consider distributions uploaded before DATE
--exclude-newer-package <PKG=DATE> Same, per package
--no-sources                       Ignore tool.uv.sources (resolve against published metadata)
--no-sources-package <PKG>         Ignore sources for one package
```

**Installer options**

```text
--reinstall                        Reinstall everything
--reinstall-package <PKG>          Reinstall one package
--link-mode <clone|copy|hardlink|symlink>
--compile-bytecode                 Compile .py to .pyc after install
```

**Build options**

```text
-C, --config-setting <KEY=VALUE>   Pass settings to the PEP 517 build backend
--config-settings-package <PKG:KEY=VALUE>
--no-build-isolation               Build sdists without an isolated environment
--no-build / --no-build-package    Do not build source distributions
--no-binary / --no-binary-package  Do not use pre-built wheels
```

**Cache options**

```text
--refresh                          Refresh all cached data
--refresh-package <PKG>            Refresh cached data for one package
```

**Python options**

```text
-p, --python <REQUEST>             Interpreter to use (e.g. 3.12, cpython@3.13, full path)
```

## Project commands

### `uv init`

```text
uv init [OPTIONS] [PATH]
```

Creates `pyproject.toml`, `.python-version`, `.gitignore`, `README.md`, and `src/<package>/__init__.py` (plus `.git/` for git projects).

```text
--name <NAME>              Project name (defaults to the directory name)
--bare                     Only create a pyproject.toml
--package / --no-package   Buildable package (src layout) vs application
--app / --lib              Alias for application vs library setup
--script                   Create a PEP 723 script instead of a project
--description <TEXT>       Set project description (--no-description to omit)
--vcs <git|none>           Initialize a version control system
--build-backend <uv|hatch|flit|pdm|poetry|setuptools|maturin|scikit>
                           Build backend (default uv, i.e. uv_build)
--author-from <auto|git|none>
--no-readme
--no-pin-python            Do not create .python-version
--no-workspace             Standalone project even inside a workspace
```

### `uv add`

```text
uv add [OPTIONS] <PACKAGES... | -r REQUIREMENTS>
```

`PACKAGES` are PEP 508 requirements, e.g. `ruff==0.5.0`, `"httpx>=0.20"`, `"jax; sys_platform == 'linux'"`. By default uv appends a lower bound for the latest compatible version (`>=1.2.3`) — pass an explicit constraint or `--raw` to control what is written. Adds to `[project.dependencies]` unless a placement flag is given, then re-locks and syncs.

```text
Placement
  --dev                    To [dependency-groups] dev
  --group <NAME>           To [dependency-groups] NAME
  --optional <EXTRA>       To [project.optional-dependencies] EXTRA
  --script <FILE>          To the PEP 723 metadata block of FILE

Constraints and input
  -r, --requirements <FILE>    Add packages listed in requirements files
  -c, --constraints <FILE>     Constrain versions using files
  --raw                      Add the dependency exactly as provided (no bounds,
                              no tool.uv.sources relocation)
  --bounds <lower|major|minor|exact>   Version bound style when uv picks one
  -m, --marker <MARKER>      Apply an environment marker to all added packages
  --extra <EXTRA>            Enable extras on the added dependency

Sources
  --editable               Install a directory dependency as editable
  --rev / --tag / --branch Git references for git+ URLs (mutually exclusive)
  --lfs                    Fetch Git LFS objects for git sources
  --workspace / --no-workspace  Control auto-addition as workspace member

Environment and lock
  --no-sync                Do not sync the venv after re-locking
  --locked / --frozen      Assert lockfile unchanged / skip re-locking
  --active                 Prefer the active virtual environment
  --package <PKG>          Target a specific workspace member
  --no-install-project / --no-install-workspace / --no-install-local
  --no-install-package <PKG>
```

### `uv remove`

```text
uv remove [OPTIONS] <PACKAGES...>
```

Removes from `[project.dependencies]` by default; also removes the corresponding `tool.uv.sources` entry if it is no longer referenced.

```text
--dev / --group <NAME> / --optional <EXTRA>   Placement, as with uv add
--script <FILE>            Remove from a PEP 723 script
--no-sync / --locked / --frozen
--active / --package <PKG>
```

### `uv sync`

```text
uv sync [OPTIONS]
```

Installs (and, by default, removes) packages so the environment matches the lockfile. Installs the project and workspace members as editable by default (unless they lack a build system).

```text
Extras
  --extra <NAME> / --all-extras / --no-extra <NAME>

Groups
  --no-dev / --only-dev
  --group <NAME> / --no-group <NAME> / --only-group <NAME> / --all-groups
  --no-default-groups

Environment
  --inexact                Do not remove extraneous packages (default is exact)
  --check                  Only check that the environment is in sync
  --dry-run                Show changes without applying
  --active                 Sync the active virtual environment
  --no-editable / --no-editable-package <PKG>
  --no-install-project / --no-install-workspace / --no-install-local
  --no-install-package <PKG>
  --python-platform <PLATFORM>   Install for a target platform (Docker layering)

Workspace and scripts
  --all-packages / --package <PKG>
  --script <FILE>          Sync for a PEP 723 script

Locking
  --locked / --frozen      As with other commands
  (plus the shared index, resolver, installer, build, cache, python groups)
```

### `uv lock`

```text
uv lock [OPTIONS]
```

Resolves the project (or workspace) and writes `uv.lock`. Prefers locked versions; use `--upgrade` / `--upgrade-package` to move them.

```text
--check          Verify the lockfile is up-to-date, without writing
--check-exists   Assert that uv.lock exists, without checking freshness
--dry-run        Resolve without writing
--script <FILE>  Lock a PEP 723 script (creates <file>.py.lock)
(plus the shared index, resolver, build, installer, cache, python groups)
```

### `uv export`

```text
uv export [OPTIONS]
```

Exports `uv.lock` to an alternate format (stdout by default).

```text
--format <requirements.txt|pylock.toml|cyclonedx1.5>
-o, --output-file <FILE>
--all-packages / --package <PKG>   Workspace scope
--prune <PKG>                      Prune a package from the tree
Extras and group flags (same as uv sync)
--no-annotate / --no-header        Strip comments
--no-hashes
--emit-index-url / --emit-find-links   Include index configuration in output
--no-editable / --no-emit-project / --no-emit-workspace / --no-emit-local
--no-emit-package <PKG>
--locked / --frozen
--script <FILE>
(plus the shared index, resolver, build, installer, cache, python groups)
```

### `uv run`

```text
uv run [OPTIONS] [COMMAND]...
```

Runs a command in the project environment, locking and syncing first. `uv run python main.py`, `uv run pytest`, or `uv run -- flask run -p 3000` (everything after `--` goes to the command).

```text
-m, --module               Treat the command as a Python module
-s, --script               Treat the first argument as a PEP 723 script
--gui-script               Run a .pyw via pythonw (Windows)
-w, --with <REQ>           Install extra packages for this run (repeatable)
   --with-editable <REQ> / --with-requirements <FILE>
--isolated                 Run in a fresh isolated environment (no project deps)
--no-project               Do not discover/install the project
--active                   Use the active virtual environment
--env-file <FILE>          Load variables from a dotenv file (repeatable)
--no-env-file
--exact                    Exact sync (remove extraneous packages; default is inexact)
Extras and group flags (same as uv sync)
--all-packages / --package <PKG>
--python-platform <PLATFORM>
--no-sync / --locked / --frozen
(plus the shared index, resolver, installer, build, cache, python groups)
```

Note: in a project, `uv run <script>.py` installs the project first; use `--no-project` for standalone scripts. PEP 723 scripts declared via `--script` (or with an inline metadata block) ignore the project.

### `uv tree`

```text
uv tree [OPTIONS]
--universal        Platform-independent view of the lockfile
--format <text|json>
-d, --depth <N>    Max display depth (default 255)
--prune <PKG>      Hide a package and its subtree
--package <PKG>    Show only specific packages
--no-dedupe        Repeat sub-trees instead of marking them (*)
--invert           Show reverse dependencies
--outdated         Show which packages have newer versions
--script <FILE>
```

### `uv audit`

```text
uv audit [OPTIONS]
--output-format <text|json|sarif>
--ignore <ID>      Ignore a vulnerability by advisory ID (repeatable)
Group flags (same as uv sync): --no-dev, --group, --no-group, --only-group,
--all-groups, --no-default-groups, --only-dev
--locked / --frozen
```

Checks the lockfile against OSV.dev (security advisories). Preview `audit.malware-check = true` also scans for known malicious packages during sync.

### `uv format` and `uv check`

```text
uv format [OPTIONS] [-- EXTRA_ARGS...]
--check            Check formatting without applying
--diff             Show the diff of changes
--version <V>      Ruff version to use

uv check [OPTIONS]
--fix              Apply safe fixes
--script <FILE>    Check a PEP 723 script
--all-packages / --package <PKG>
Extras and group flags (same as uv sync)
--no-sync / --locked / --frozen
--isolated
```

`uv format` runs Ruff (managed by uv, not the project); `uv check` runs the ty type checker. Both download the tool into the uv cache rather than requiring a system install.

### `uv version`

```text
uv version [OPTIONS] [VALUE]
--bump <major|minor|patch|stable|alpha|beta|rc|post|dev[=N]>
                   Bump the version semantically (repeatable, applied largest to smallest)
--dry-run          Preview without writing
--short            Print only the version string
--output-format <text|json>
--no-sync / --locked / --frozen
--package <PKG>    Target a workspace member
```

### `uv build`

```text
uv build [OPTIONS] [SRC]
-o, --out-dir <DIR>     Output directory (default dist/)
--sdist / --wheel       Build only one artifact type
--package <PKG> / --all-packages
--no-build-logs
--force-pep517
--clear                 Remove stale artifacts first
```

Builds through the project's `[build-system]`; without one, falls back to legacy setuptools for `uv build` (but the project is skipped during `uv sync`).

### `uv publish`

```text
uv publish [OPTIONS] [FILES...]     # default FILES is dist/* (globs accepted)
-t, --token <TOKEN>          PyPI token (or UV_PUBLISH_TOKEN)
-u, --username / -p, --password
--trusted-publishing <automatic|always|never>
--index <NAME>               Publish to a configured [[tool.uv.index]] (needs publish-url)
--publish-url <URL>          Upload endpoint (not the index URL)
--check-url <URL>            Skip files that already exist in the registry
--dry-run
--no-attestations            Do not upload PEP 740 attestations (auto-discovered as
                             <file>.publish.attestation next to dist artifacts)
```

### `uv workspace`

```text
uv workspace list          List workspace members
uv workspace dir <MEMBER>  Path of a workspace member
uv workspace metadata      Machine-readable workspace metadata
```

## Python and environments

### `uv python`

```text
uv python list             List available Python installations (managed + discovered)
uv python install <REQ>    Download and install (e.g. 3.12, cpython@3.13, pypy@3.10)
uv python upgrade          Upgrade installed versions to the latest patch
uv python find [REQ]       Find an interpreter matching a request
uv python pin [REQ]        Write .python-version (--resolved to pin the exact path,
                           --global for the global pin, --rm to remove)
uv python dir              Show the managed installation directory
uv python uninstall <REQ>  Remove a managed Python
uv python update-shell     Ensure the Python executable directory is on PATH
```

### `uv venv`

```text
uv venv [OPTIONS] [PATH]     # default path .venv
-p, --python <REQUEST>       Interpreter to base the environment on
--seed                       Install pip, setuptools, and/or wheel
-c, --clear                  Remove existing files at the target path
--force                      Allow --clear on non-virtual-environment dirs
--allow-existing             Preserve existing files
--prompt <TEXT>              Custom prompt prefix
--system-site-packages
--relocatable
--link-mode <clone|copy|hardlink|symlink>
--no-project                 Do not discover the surrounding project
```

`uv venv` only creates the environment. Use `uv sync` / `uv run` to install project dependencies, or `uv pip install` for manual management.

## Tools

`uvx` is a standalone alias of `uv tool run`.

```text
uv tool run [OPTIONS] [COMMAND]      # uvx ruff check .
--from <PKG>          Provide the command from a specific package (when tool name differs)
-w, --with <REQ>      Extra packages in the tool environment (repeatable)
   --with-editable <REQ> / --with-requirements <FILE>
-c, --constraints <FILE> / -b, --build-constraints <FILE> / --overrides <FILE>
--isolated            Ignore already-installed tools
--env-file <FILE> / --no-env-file
--python-platform <PLATFORM>
--lfs / -p, --python <REQ>

uv tool install [PKG]     # install user-wide (--from, --force, --with, -p, ...)
uv tool upgrade [--all]
uv tool list
uv tool audit             # audit installed tools and dependencies
uv tool uninstall <NAME>
uv tool dir
uv tool update-shell      # ensure tool bin dir is on PATH
```

Tools run in isolated environments under uv's data directory (see `uv tool dir`), separate from any project. Inside a project, prefer `uv run <tool>` when the tool needs the project installed.

## pip interface

Legacy/manual environment management. These operate on the *active* environment (discovered via `VIRTUALENV`/`VIRTUAL_ENV` or `--python`), not on the project lockfile.

```text
uv pip install <REQS...>     # -r, -c, -U, --no-deps, --dry-run, ...
uv pip uninstall <PKGS...>
uv pip list
uv pip show <PKG>
uv pip freeze
uv pip check                 # check environment consistency
uv pip tree
uv pip compile [REQS]        # resolve to a locked output (requirements.txt or pylock.toml)
uv pip sync <REQS>           # make the environment exactly match requirements
```

Configure pip-interface-only settings under `[tool.uv.pip]` in `pyproject.toml`.

## Utilities

```text
uv cache clean [PKG...]   # clear all or specific entries
uv cache prune            # remove dangling entries and unused environments
uv cache dir
uv cache size

uv self update            # self-update uv
uv self version

uv auth login <SERVICE>   # store credentials
uv auth logout <SERVICE>
uv auth token <SERVICE>
uv auth dir
```
