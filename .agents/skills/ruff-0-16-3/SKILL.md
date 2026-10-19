---
name: ruff-0-16-3
description: >
  Ruff 0.16.3 — an extremely fast Python linter and code formatter written in Rust,
  a drop-in replacement for Flake8 (plus plugins), Black, isort, pydocstyle,
  pyupgrade, and autoflake. Use this skill when the user wants to lint, format, or
  auto-fix Python code with ruff, configure ruff in pyproject.toml, ruff.toml, or
  .ruff.toml, select or ignore lint rules, suppress violations with noqa or ruff
  ignore comments, migrate a project from Black, Flake8, or isort, or wire ruff
  into pre-commit, GitHub Actions, GitLab CI, or Docker. Covers ruff check,
  ruff format, rule selection, fix safety, error suppression, preview mode, and
  the expanded 0.16 default rule set.
metadata:
  tags:
    - python
    - linting
    - formatting
    - tooling
---

# ruff 0.16.3

## Overview

Ruff is an extremely fast Python linter and code formatter, written in Rust and
distributed as a single binary. It is 10-100x faster than Flake8 or Black and
replaces Flake8 (plus dozens of plugins), Black, isort, pydocstyle, pyupgrade, and
autoflake behind one CLI.

- **Version** — 0.16.3 (2026-08-13). Supports Python 3.7 through 3.15
  (`target-version` values `py37`–`py315`); Python 2 is not supported.
- **Scale** — over 900 lint rules re-implemented natively from 50+ upstream tools
  (flake8-bugbear, pylint, flake8-bandit, isort, pydocstyle, …).
- **Two tools in one** — `ruff check` (linter, with auto-fixes) and `ruff format`
  (Black-compatible formatter). They can be used independently.
- **Headline change in the 0.16 line** — 0.16.0 expanded the default rule set from
  59 to 413 rules. Upgrading into 0.16.x surfaces many new diagnostics on
  existing code.

Install (pre-built wheels; no Rust toolchain needed):

```shell
uv tool install ruff@latest      # global
uv add --dev ruff                # per project
pip install ruff                 # or: pipx install ruff, brew install ruff
uvx ruff check                   # run without installing
```

Subcommands: `check`, `format`, `rule` (explain a rule), `config` (describe a
setting), `linter` (list upstream linters), `clean` (clear caches), `server`
(language server), `analyze graph` (dependency/dependent map), `version`.

## Usage

### Lint

```shell
ruff check                      # lint current directory recursively
ruff check src/                 # a directory (recursively) or
ruff check path/to/file.py      # explicit files (always analyzed, see Gotchas)
ruff check -                    # stdin (pair with --stdin-filename)
ruff check --fix                # apply safe fixes
ruff check --fix --unsafe-fixes # also apply unsafe fixes (may change behavior)
ruff check --fix --diff         # preview fixes as a diff, write nothing
ruff check --watch              # re-lint on change
ruff check --select F401        # replace configured selection with F401 only
ruff check --extend-select RUF100
ruff check --statistics         # count violations per rule
ruff check --show-settings src/app.py   # resolved settings for one file
ruff check --output-format json # concise, full, json, json-lines, junit,
                                # grouped, github, gitlab, pylint, rdjson, azure, sarif
```

Exit codes: `0` no violations (or all fixed), `1` violations found, `2`
configuration/CLI error. `--exit-zero` forces `0` even with violations;
`--exit-non-zero-on-fix` exits `1` when fixes were applied, even if nothing
remains. A built-in cache (`.ruff_cache/`) skips unchanged files — use
`-n`/`--no-cache` or `ruff clean` for deterministic runs.

### Format

```shell
ruff format                 # format in place
ruff format src/            # a directory or file
ruff format --check         # CI mode; exits 1 if any file would change
ruff format --diff          # show what would change
```

The formatter does **not** sort imports. To sort and format, run both:

```shell
ruff check --select I --fix   # isort rules
ruff format
```

### Explore rules and settings

```shell
ruff rule F401            # explain one rule (usage, fix, examples)
ruff rule --all           # list every rule
ruff config line-length   # describe a configuration option
ruff linter               # list supported upstream linters (E, F, B, I, …)
```

### Configuration

Ruff reads `pyproject.toml` (`[tool.ruff]`), `ruff.toml`, or `.ruff.toml` —
same schema, with the `tool.ruff` prefix omitted in the latter two. In one
directory, `.ruff.toml` beats `ruff.toml`, which beats `pyproject.toml`.

```toml
# pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "UP", "B", "I"]
per-file-ignores = { "__init__.py" = ["E402"] }

[tool.ruff.format]
quote-style = "double"
```

Discovery rules that matter (details in
[01-configuration](references/01-configuration.md)):

- The **closest** config file in the file's directory hierarchy wins for that
  file; configs are **not merged** across levels. Use
  `extend = "../ruff.toml"` to inherit a parent config and override.
- A `pyproject.toml` without a `[tool.ruff]` section is ignored during
  discovery.
- If `target-version` is unset, Ruff infers it from `requires-python` in a
  nearby `pyproject.toml`.
- CLI options override config; `--config` accepts a file path or inline
  `"lint.key = value"` TOML pairs; `--isolated` ignores all config files.
- Very long argument lists can be read from a file with `@args.txt`
  (one argument per line).

### Rule selection

Selectors accept a full rule code (`F401`) or any valid prefix (`F`, `E`,
`UP`, …). The 0.16 default set covers 413 rules. `select` defines the set,
`extend-select` adds to it, `ignore` removes from it. `ALL` enables every
stable rule (conflicting docstring styles like `D203`/`D211` are auto-disabled).
CLI selections have higher priority than file selections. Rules in preview
only fire when preview mode is on — see
[02-rule-selection](references/02-rule-selection.md) for precedence, preview,
and fix safety.

### Error suppression

```python
import os  # noqa: F401          # line-level, suppress F401 on this line
x = 1  # noqa                    # blanket (all rules on the line)

# ruff: ignore[ARG001]           # line-level, covers the whole logical line
def foo(arg1, arg2): pass

# ruff: disable[E501]            # block-level range…
VALUE = "a very long string"
# ruff: enable[E501]             # …closed explicitly (preferred)

# ruff: noqa                      # file-level (any line, prefer top)
# ruff: noqa: F841                # file-level, one rule
# ruff: file-ignore[F401, ARG001] # file-level, explicit list
```

`RUF100` (`unused-noqa`) detects suppressions that no longer match anything;
`--add-noqa` / `--add-ignore` back-fill suppressions when adopting a new rule.
Full semantics in [03-error-suppression](references/03-error-suppression.md).

### pre-commit / CI

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.16.3
  hooks:
    - id: ruff-check
      args: [--fix]
    - id: ruff-format
```

GitHub Actions, GitLab CI, Docker, and editor setup are in
[05-integrations](references/05-integrations.md).

## Gotchas

- **0.16.0 grew the default rule set from 59 to 413 rules** — upgrading into
  the 0.16 line surfaces many new findings. Survey with
  `ruff check --statistics`, or make the rule set explicit with `select`.
  Eighteen opinionated `E`/`F` rules (`E401`, `E402`, `E701`–`E703`,
  `E711`–`E714`, `E721`, `E731`, `E741`–`E743`, `F403`, `F405`, `F406`, `F722`)
  were *removed* from the defaults.
- **The formatter does not sort imports** — run `ruff check --select I --fix`
  separately; there is no unified lint+format command.
- **Only safe fixes apply by default** — `--fix` skips fixes that could change
  runtime behavior (e.g., exception type). Opt in per run with
  `--unsafe-fixes` or per rule via `lint.extend-safe-fixes`.
- **`E501` can still fire when `ruff format` is enabled** — the formatter
  wraps lines best-effort and never wraps comments or long strings, so
  formatted code may exceed `line-length`.
- **Some lint rules fight the formatter** — `Q000`–`Q004`, `COM812`, `COM819`,
  `D203`, `D206`, `D300`, `W191`, `E111`, `E114`, `E117`, `ISC002`
  (without `ISC001`). `ruff format` prints a warning when any is enabled;
  ignore them via `lint.ignore`.
- **Configs are not merged** — only the closest config applies to a file.
  Inherit a parent with `extend = "../ruff.toml"`; a `pyproject.toml` lacking
  `[tool.ruff]` is invisible to discovery.
- **`--config` behaves differently from discovered files** — relative paths
  inside it resolve against the *current working directory*, and its settings
  apply to *all* analyzed files (including subdirectory configs).
- **Explicitly named paths bypass `exclude`** — `ruff check build/file.py`
  lints it unless `--force-exclude` is set. Conversely, `.gitignore` rules are
  respected by default (`respect-gitignore`); pass `--no-respect-gitignore` to
  disable.
- **`--select` replaces, `--extend-select` adds** — a common mistake is
  `ruff check --select F401` when the intent was to add F401 on top of the
  configured set.
- **`include`/`extend-include` globs must match files** — `include = ["src"]`
  fails because it matches a directory.
- **noqa placement is position-sensitive** — for an import block, put
  `# noqa: I001` on the *first* line to cover the whole block; for a
  multi-line string, put it after the closing triple quote; a `# ruff:
  ignore[...]` on its own line covers the entire logical statement below it,
  while trailing/inside a multi-line statement covers only one physical line.
- **Unmatched `# ruff: disable[...]` is an implicit range** — it ends at the
  enclosing logical scope, and `RUF104` warns about that. Close ranges with an
  explicit matching `# ruff: enable[...]`.
- **Preview rules are silently inert without preview** — selecting a preview
  rule (or its prefix, or `ALL`) does nothing unless `--preview` /
  `preview = true` is set. Lint and format preview can be enabled
  independently (`lint.preview`, `format.preview`).
- **`ruff check --fix` exits 0 when everything is fixed** — CI that expects a
  failure when code changed needs `--exit-non-zero-on-fix` (or
  `--exit-non-zero-on-format` for `ruff format`).
- **Notebooks are linted and formatted by default** (since 0.6.0) — scope
  them out with the tool-specific `exclude` (`[lint]` or `[format]`) or
  `extend-exclude = ["*.ipynb"]`.
- **`target-version` defaults to `py310` when nothing is set** — and some
  rules (pyupgrade, f-string quote handling) behave differently per target.
  Set it to match the project's real minimum.

## References

- [01-configuration](references/01-configuration.md) — config files, discovery and inheritance, defaults, file discovery, CLI overrides
- [02-rule-selection](references/02-rule-selection.md) — rule codes, select/ignore precedence, ALL, preview rules, fix safety, exit codes, output formats
- [03-error-suppression](references/03-error-suppression.md) — noqa and ruff: ignore semantics, disable/enable ranges, file-level suppression, RUF100, back-filling
- [04-formatter](references/04-formatter.md) — Black compatibility and deviations, fmt pragmas, docstring and Markdown formatting, conflicting rules
- [05-integrations](references/05-integrations.md) — pre-commit, GitHub Actions, GitLab CI, Docker, editors, LSP, nbQA
