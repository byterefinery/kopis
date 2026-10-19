# CLI Reference (ty 0.0.72)

Source: https://docs.astral.sh/ty/reference/cli/

## Commands

- `ty check [OPTIONS] [PATH]...` — check a project for type errors
- `ty server` — start the language server
- `ty version [OPTIONS]` — display ty's version (`--output-format text|json`)
- `ty explain rule [OPTIONS] [RULE]` — explain a rule (defaults to all rules; `--output-format text|json`)
- `ty generate-shell-completion <SHELL>` — generate shell completion
- `ty help [COMMAND]`

## ty check

```
ty check [OPTIONS] [PATH]...
```

**Arguments**

- `PATH` — files or directories to check (default: the project root). Explicitly passed paths are included even if they would otherwise be excluded or ignored.

**Options**

- `--add-ignore` — adds `ty: ignore` comments to suppress all rule diagnostics
- `--color <auto|always|never>` — control when colored output is used (default `auto`)
- `--config` / `-c <KEY=VALUE>` — a TOML `KEY = VALUE` pair (as found in a `ty.toml`) overriding one configuration option; always takes precedence over all configuration files
- `--config-file <path>` — path to a `ty.toml` file to use (pyproject.toml is not allowed in this context); also settable via `TY_CONFIG_FILE`
- `--error <rule>` — treat the given rule as severity `error` (repeatable; `all` applies to all rules)
- `--error-on-warning` — exit code 1 if there are any warning-level diagnostics (incompatible with `--exit-zero` / `--exit-zero-on-warning`)
- `--exclude <pattern>` — gitignore-style glob patterns for files to exclude (e.g. `tests/`, `*.tmp`, `**/__pycache__/**`)
- `--exclude-scripts` — exclude files with PEP 723 inline script metadata unless passed explicitly (default off; `--include-scripts` re-enables)
- `--exit-zero` — always exit 0, even with error-level diagnostics (incompatible with `--error-on-warning`)
- `--exit-zero-on-warning` — exit 0 unless there are error-level diagnostics (incompatible with `--error-on-warning`)
- `--extra-search-path <path>` — additional module-resolution source (repeatable). Advanced; for first-/third-party modules not installed conventionally. Prefer `--python` for unusual environments
- `--fix` — apply fixes to resolve errors
- `--force-exclude` — enforce exclusions even for paths passed directly on the command line
- `--ignore <rule>` — disable the rule (repeatable; `all` disables all)
- `--no-progress` — hide spinners and progress bars
- `--output-format <full|concise|github|gitlab|junit>` — diagnostic output format (also via `TY_OUTPUT_FORMAT`); `full` is the verbose default
- `--project <dir>` — run within the given project directory; `pyproject.toml` discovery and `.venv` lookup walk up from it, while other CLI arguments resolve relative to the cwd
- `--python` / `--venv <path>` — path to the Python environment or interpreter ty uses to resolve third-party imports. Accepts an interpreter (`.venv/bin/python3`), a venv directory (`.venv`), or a `sys.prefix` directory (`/usr`)
- `--python-platform` / `--platform <platform>` — target platform for `sys.platform` specialization (`win32`, `darwin`, `android`, `ios`, `linux`, `all`, or a custom string); default is the current platform
- `--python-version` / `--target-version <version>` — Python version to assume (`3.7`..`3.15`); affects syntax, stdlib types, and version-conditional first/third-party types. Inference order: CLI/config, then `project.requires-python` minimum, then active environment, then latest stable supported (3.14 in 0.0.72)
- `--quiet` / `-q` — quiet output (`-qq` for silent)
- `--respect-ignore-files` — respect exclusions from `.gitignore` and other standard ignore files (default on; `--no-respect-ignore-files` disables)
- `--typeshed` / `--custom-typeshed-dir <path>` — custom directory for stdlib typeshed stubs (default: vendored stubs)
- `--verbose` / `-v` — verbose output (`-vv`, `-vvv` for more)
- `--warn <rule>` — treat the given rule as severity `warn` (repeatable; `all` applies to all)
- `--watch` / `-W` — watch files for changes and re-check changed files plus their dependents (fine-grained incrementality)

## Environment variables

ty-defined:

- `TY_CONFIG_FILE` — path to a `ty.toml` (equivalent to `--config-file`)
- `TY_LOG` — log level for `--verbose` output (tracing filter syntax, e.g. `ty=debug`)
- `TY_LOG_PROFILE` — `1`/`true` enables flamegraph profiling (writes `tracing.folded`)
- `TY_MAX_PARALLELISM` — cap on parallel tasks (equivalent to `RAYON_NUM_THREADS`)
- `TY_OUTPUT_FORMAT` — same values as `--output-format`

Externally defined:

- `CONDA_DEFAULT_ENV`, `CONDA_PREFIX`, `_CONDA_ROOT` — active Conda environment detection
- `PYTHONPATH` — adds directories to module search paths
- `VIRTUAL_ENV` — activated venv detection (preferred over `CONDA_PREFIX`)
- `XDG_CONFIG_HOME` — user-level config directory on Unix
