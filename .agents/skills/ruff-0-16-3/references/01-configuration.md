# Ruff Configuration (0.16.3)

Table of contents

- [Config files](#config-files)
- [Default configuration](#default-configuration)
- [Config file discovery](#config-file-discovery)
- [Inheriting configs with `extend`](#inheriting-configs-with-extend)
- [Inferring the Python version](#inferring-the-python-version)
- [Python file discovery](#python-file-discovery)
- [Jupyter Notebooks](#jupyter-notebooks)
- [CLI overrides](#cli-overrides)
- [Argfile support](#argfile-support)
- [Shell autocompletion](#shell-autocompletion)

## Config files

Ruff reads its configuration from one of:

- `pyproject.toml` — settings under a `[tool.ruff]` section (and `[tool.ruff.lint]`, `[tool.ruff.format]`, … subsections)
- `ruff.toml` — identical schema without the `tool.ruff` prefix (`[lint]`, `[format]`, …)
- `.ruff.toml` — same as `ruff.toml`, but takes precedence over it in the same directory

INI-style files (`setup.cfg`, `tox.ini`) are not supported. Linter plugin
options live in their own subsections, e.g. `[tool.ruff.lint.pydocstyle]` with
`convention = "google"`.

```toml
# pyproject.toml
[tool.ruff.lint]
extend-select = ["B"]       # 1. enable flake8-bugbear on top of defaults
ignore = ["E501"]           # 2. skip line-too-long
unfixable = ["B"]           # 3. never auto-fix B rules

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["E402"]
"**/{tests,docs,tools}/*" = ["E402"]

[tool.ruff.format]
quote-style = "single"      # 4. formatter uses single quotes
```

## Default configuration

With no config file, Ruff behaves as if given:

```toml
exclude = [
  ".bzr", ".direnv", ".eggs", ".git", ".git-rewrite", ".hg",
  ".ipynb_checkpoints", ".mypy_cache", ".nox", ".pants.d", ".pyenv",
  ".pytest_cache", ".pytype", ".ruff_cache", ".svn", ".tox", ".venv",
  ".vscode", "__pypackages__", "_build", "buck-out", "build", "dist",
  "node_modules", "site-packages", "venv",
]
line-length = 88
indent-width = 4
target-version = "py310"

[lint]
# select = [...]   # 413 default rules in the 0.16 line; see the
#                  # "Default Rules" page at docs.astral.sh/ruff
ignore = []
fixable = ["ALL"]
unfixable = []
dummy-variable-rgx = "^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$"

[format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
docstring-code-format = false
docstring-code-line-length = "dynamic"
```

## Config file discovery

Ruff supports hierarchical (per-directory) configuration: for every file, the
*closest* config file in that file's directory or any parent is used, and all
relative paths in it (`exclude` globs, `src`) resolve against the directory
containing that config file.

Exceptions and fine print:

1. When searching for a `pyproject.toml`, any file **lacking a `[tool.ruff]`
   section is skipped**.
2. A config passed via `--config` is used for *all* analyzed files, and its
   relative paths resolve against the *current working directory*.
3. If no config is found in the filesystem hierarchy, Ruff falls back to a
   user-level config at `${config_dir}/ruff/pyproject.toml`
   (`~/.config/ruff/…` on Linux/macOS, respecting `XDG_CONFIG_HOME`;
   `%AppData%\ruff\…` on Windows), else built-in defaults.
4. Any setting given on the command line (e.g. `--select`) overrides the
   setting in *every* resolved config file.

Precedence when several config files sit in the same directory:
`.ruff.toml` > `ruff.toml` > `pyproject.toml`.

## Inheriting configs with `extend`

Unlike ESLint, Ruff does **not** merge parent and child configs — the closest
config fully replaces its parents. To inherit, use the `extend` field:

```toml
[tool.ruff]
extend = "../pyproject.toml"   # inherit parent settings…
line-length = 100              # …but override this one
```

When a config uses `extend`, the *project root* for `src` resolution is still
the directory containing the extending file, not the extended one. If you add
a nested config (e.g. in `tests/`) that extends the root, re-point `src`
explicitly, e.g. `src = ["../src"]`.

## Inferring the Python version

If no discovered config sets `target-version`, Ruff infers it from
`requires-python` in a `pyproject.toml`:

1. `--config` passed explicitly — no inference.
2. A config found in the hierarchy — inferred from `requires-python` in the
   `pyproject.toml` *in the same directory* as the found config.
3. User-level config in use — `requires-python` from the first `pyproject.toml`
   in an ancestor of the CWD wins.
4. No config at all — inferred from the first `pyproject.toml` in an ancestor
   of the CWD (behavior can therefore vary by working directory).

## Python file discovery

Given a path argument, Ruff discovers Python files recursively, subject to
`exclude` / `extend-exclude` in each directory's config.

- **Default inclusions** — `*.py`, `*.pyi`, `*.ipynb`, and `pyproject.toml`
  (plus `*.pyw` in preview mode). Change with `include`; add with
  `extend-include`. Globs in both **must match files**, not directories
  (`include = ["src"]` is invalid; use `src/**/*.py`).
- **Per-tool exclusions** — `exclude` can be scoped to `[lint]` or `[format]`
  so a file is linted but not formatted (e.g. `[format] exclude = ["*.pyi"]`
  or `["*.ipynb"]`).
- **gitignore** — files matched by `.ignore`, `.gitignore`,
  `.git/info/exclude`, or global gitignore are skipped by default
  (`respect-gitignore`; disable with `--no-respect-gitignore`).
- **Explicit paths** — files passed directly on the command line are always
  analyzed even if excluded, unless `--force-exclude` is enabled.
- **Custom extensions** — `--extension ipy:ipynb` (or the `extension` config)
  maps file extensions to a language (`python`, `ipynb`, `pyi`, `markdown`).

## Jupyter Notebooks

Notebooks (`.ipynb`) are linted **and** formatted by default since 0.6.0.

- Lint-only or format-only: use the tool-specific `exclude`
  (`[lint] exclude = ["*.ipynb"]` or `[format] exclude = ["*.ipynb"]`).
- Disable entirely: `extend-exclude = ["*.ipynb"]`.
- Notebook-specific ignores: `per-file-ignores = { "*.ipynb" = ["T20"] }`.
- Some rules change meaning in notebooks — e.g. `E402` detects imports not at
  the top of a *cell* rather than a file. Rule docs note such cases.

## CLI overrides

Dedicated flags exist for common options (`--select`, `--ignore`,
`--line-length`, `--exclude`, …). Everything else can be overridden with the
catch-all `--config`:

```shell
# Point at a file
ruff check src --config path/to/ruff.toml

# Inline TOML key=value pairs (repeatable); linter settings need the lint. prefix
ruff check file.py \
  --config "lint.dummy-variable-rgx = '__.*'" \
  --config "lint.per-file-ignores = {'some_file.py' = ['F841']}"

# A dedicated flag beats --config for the same setting
ruff format file.py --line-length=90 --config "line-length=100"   # -> 90
```

`--config "line-length=90"` overrides that setting in *all* discovered config
files, including ones in subdirectories. `--isolated` ignores all config files
entirely (useful in CI and tests).

## Argfile support

Prefix an argument file with `@`; each line is one argument. This keeps long
path lists out of the shell command line:

```shell
ruff check @args.txt
```

```text
--select
F401
--quiet
path/to/code1/
path/to/code2/
```

## Shell autocompletion

Generate a completion script for `bash`, `zsh`, `fish`, `elvish`, or
`powershell`:

```shell
echo 'eval "$(ruff generate-shell-completion zsh)"' >> ~/.zshrc
```

Then restart the shell or source the rc file.
