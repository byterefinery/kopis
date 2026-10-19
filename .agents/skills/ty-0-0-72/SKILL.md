---
name: ty-0-0-72
description: Extremely fast Python type checker and language server (ty 0.0.72) written in Rust by Astral. Use when the user wants to type-check Python code with ty, run ty check or ty server, configure ty in pyproject.toml or ty.toml, set rule severity, suppress diagnostics with ty or type ignore comments, control the target Python version or platform, resolve import errors, or migrate from mypy or Pyright. Covers installation, CLI reference, rules, configuration, suppression, and exit codes.
license: MIT
compatibility: Requires the ty 0.0.72 binary (uvx ty, uv tool install ty, pip install ty, or the standalone installer); the standalone build does not require a Python interpreter
metadata:
  tags:
    - python
    - type-checking
    - cli
    - linter
---

# ty 0.0.72

## Overview

ty is an extremely fast Python type checker and language server, written in Rust, by Astral (creators of uv and Ruff). It type checks large projects (home-assistant/core in seconds, uncached) and is 10x-100x faster than mypy or Pyright.

Two main commands:

- `ty check` — type checks a project or given paths, with configurable rule severities, per-file overrides, and an incremental watch mode
- `ty server` — language server for editor integration (not for headless use)

Diagnostics are rich: source context, references to the relevant definition, helpful explanations (e.g. why `tomllib` is missing when targeting 3.10), and suggested fixes. ty is designed for gradual adoption — redeclarations and partially typed code are supported, and untyped function bodies are checked unconditionally.

Status is **beta** (0.0.x): breaking changes, including to diagnostics, may occur between versions. Officially supported target: Python 3.10+; 3.7-3.9 can be selected but may give false positives/negatives due to missing bundled stdlib stubs.

## Usage

### Getting started

```bash
uvx ty check          # try without installing
uv add --dev ty && uv run ty check   # pin a version in the project (recommended)
uv tool install ty    # or install globally
ty check              # check the project (all Python files under the project root or cwd)
ty check src file.py  # check specific files/directories
ty check --watch      # re-check incrementally as files change
ty explain rule invalid-assignment   # explain one rule (or all rules if omitted)
```

**Environment discovery** — ty resolves third-party imports through `VIRTUAL_ENV` (or an activated Conda env), then a `.venv` at the project root or cwd, then a `python3`/`python` binary on `PATH`. Run via `uv run` or with an activated env and discovery just works; otherwise point `--python` (alias `--venv`) at an interpreter, a venv directory, or a `sys.prefix` directory.

### Configuration

- Project config: `[tool.ty]` table in `pyproject.toml`, or a `ty.toml` file (same structure, no `tool.ty` prefix). Searched in the cwd and up the directory tree. **`ty.toml` wins over `pyproject.toml`** when both exist in one directory.
- User config: `~/.config/ty/ty.toml` (or `$XDG_CONFIG_HOME/ty/ty.toml`); project settings take precedence, arrays merge.
- Overrides: `--config KEY=VALUE` for a single option (always wins), `--config-file PATH` (or `TY_CONFIG_FILE`) to force a specific file (ty.toml format only).

```toml
# pyproject.toml
[tool.ty.rules]
division-by-zero = "ignore"
possibly-unresolved-reference = "warn"
```

Full option reference: [02-configuration](references/02-configuration.md).

### Rule levels

Every rule has a level — `error`, `warn`, or `ignore`. Set levels on the command line (`--warn`, `--error`, `--ignore`; repeatable, `all` targets every rule; later options override earlier ones) or in the `[tool.ty.rules]` config section. Rule names and defaults: [03-rules](references/03-rules.md), or run `ty explain rule <name>`.

Exit code behavior: **by default `terminal.error-on-warning` is `true`, so any warning also exits 1**. For a warnings-are-ok CI gate, pass `--exit-zero-on-warning` (exit 1 only on error-level findings) or set `terminal.error-on-warning = false`.

| Exit code | Meaning |
|---|---|
| 0 | no warning-or-higher diagnostics |
| 1 | warning- or error-level diagnostics found |
| 2 | invalid CLI options, invalid configuration, or IO error |
| 101 | internal error |

### Suppressing diagnostics

Inline, at the end of the offending line (for multi-line violations, the first or last line):

```py
a = 10 + "test"  # ty: ignore[unsupported-operator]
```

- Enumerate rules with commas `# ty: ignore[missing-argument, invalid-argument-type]`; always name the rules — a bare `# ty: ignore` suppresses everything on the line and is discouraged.
- Whole file: `# ty: ignore[<rule>]` on its own line before any Python code.
- Standard `type: ignore` (all on the line) and `type: ignore[ty:<rule>]` are respected; `@no_type_check` suppresses an entire function (not classes). Details: [04-suppression](references/04-suppression.md).

### Output and CI

`--output-format` (env `TY_OUTPUT_FORMAT`): `full` (default, with context), `concise` (one per line), `github`, `gitlab`, `junit` — the last three for CI reports. `--quiet`/`--quiet --quiet` reduce chatter; `--no-progress` hides spinners.

## Gotchas

- **Warnings fail by default** — in 0.0.72 `terminal.error-on-warning` defaults to `true`, so a run with only warnings exits 1. The prose rules guide says the opposite (exit 0); the auto-generated configuration reference and the flag docs agree on the `true` default — trust the config reference.
- **Positional paths bypass excludes** — paths passed directly to `ty check` are checked even if `src.exclude` or `.gitignore` would ignore them; use `--force-exclude` to enforce exclusions anyway.
- **Python version inference order** — CLI/config first, then the *minimum* of `project.requires-python` in `pyproject.toml`, then the active environment, then the latest stable version ty supports (3.14 in 0.0.72). Setting `python-version` below 3.10 risks stdlib false positives/negatives.
- **`unresolved-import` is usually an environment problem** — before disabling the rule or adding `allowed-unresolved-imports`, verify env discovery (`.venv`, `VIRTUAL_ENV`, `--python`). `replace-imports-with-any = ["pandas.**"]` is the escape hatch for modules whose types ty should simply not analyze; unlike `allowed-unresolved-imports` it also applies to resolvable modules and types them as `Any`.
- **`ty.toml` beats `pyproject.toml`** — if both exist in the same directory, the `[tool.ty]` section is ignored entirely.
- **PEP 723 scripts are special** — files with `# /// script` inline metadata use their own environment and their `requires-python` (not the project's `requires-python` or `.venv`), and are checked as part of the project by default. Exclude them with `--exclude-scripts` (or `src.exclude-scripts = true`); `--include-scripts` re-includes them.
- **No strict mode exists** — ty's default is already stricter than mypy/Pyright defaults (checks untyped function bodies, infers `[1, "foo"]` as `list[int | str]`); there is no `--check-untyped-defs` or `strictListInference` equivalent. To approximate strict, see [05-migration](references/05-migration.md).
- **Beta API** — 0.0.x means diagnostics and config options can change between versions; pin the version (`uv add --dev 'ty==0.0.72'` or `uv tool install ty@0.0.72`) where reproducibility matters.

## References

- [01-cli-reference](references/01-cli-reference.md) — full options for `ty check`, `ty explain`, `ty server`, `ty version`, plus environment variables
- [02-configuration](references/02-configuration.md) — all configuration options with defaults: rules, analysis, environment, overrides, src, terminal
- [03-rules](references/03-rules.md) — all 126 rules with their default levels and one-line descriptions
- [04-suppression](references/04-suppression.md) — suppression comments, standard `type: ignore`, `@no_type_check`, unused-ignore rules
- [05-migration](references/05-migration.md) — coming from mypy or Pyright: migration tips, strict-mode approximation, rule mapping table
