# Configuration Reference (ty 0.0.72)

Source: https://docs.astral.sh/ty/reference/configuration/

- [Configuration file discovery](#configuration-file-discovery)
- [rules](#rules) — rule severities
- [analysis](#analysis) — `allowed-unresolved-imports`, `replace-imports-with-any`, `respect-type-ignore-comments`, `strict-equality-semantics`, `strict-generic-narrowing`
- [environment](#environment) — `extra-paths`, `python`, `python-platform`, `python-version`, `root`, `typeshed`
- [overrides](#overrides) — per-file configuration
- [src](#src) — `include`, `exclude`, `exclude-scripts`, `respect-ignore-files`
- [terminal](#terminal) — `error-on-warning`, `output-format`

## Configuration file discovery

- ty searches for `pyproject.toml` (read from the `[tool.ty]` table; a `pyproject.toml` without `tool.ty` is skipped) or `ty.toml` (same structure, no prefix) in the cwd and in parent directories.
- **`ty.toml` takes precedence over `pyproject.toml`** in the same directory.
- User-level config: `~/.config/ty/ty.toml` (Unix) or `%APPDATA%\ty\ty.toml` (Windows); project settings win, arrays merge (project entries appended after user entries).
- Command-line settings beat all file configuration.

Pattern syntax (all pattern options): gitignore-like. `*` matches any characters except `/`; `**` must be a whole path component (zero or more components); `?` one character except `/`; `[abc]`, `[0-9]` character classes; `!pattern` negates; all patterns are **anchored to the project root** (`src` matches only `<root>/src`, use `**/src` for any directory named `src`).

## `rules`

Dict of rule names (or `all` for a default severity on every rule) to `ignore` | `warn` | `error`.

```toml
[tool.ty.rules]
possibly-unresolved-reference = "warn"
division-by-zero = "ignore"
```

## `analysis`

### `allowed-unresolved-imports`

List of module glob patterns for which `unresolved-import` is suppressed. `*` matches within one component (`foo.*` matches `foo.bar` but not `foo.bar.baz`), `**` matches any number of components, `!` excludes. Later entries win. Default `[]`.

```toml
[tool.ty.analysis]
allowed-unresolved-imports = ["test.**", "!test.foo"]
```

### `replace-imports-with-any`

List of module glob patterns whose imports are replaced with `typing.Any` — **even if the module resolves**. Import diagnostics are unconditionally suppressed for matching modules. `!` excludes; later entries win. Default `[]`.

```toml
[tool.ty.analysis]
replace-imports-with-any = ["pandas.**", "numpy.**"]
```

### `respect-type-ignore-comments`

Whether `type: ignore` comments suppress ty errors (default `true`). Set `false` to make ty ignore them (use `ty: ignore` instead).

### `strict-equality-semantics`

Default `false`. When `true`, ty makes no assumptions about `==` for narrowing: no `Literal` narrowing from equality checks (e.g. `if x == "a"` keeps `x` as `str`, not `Literal["a"]`), no assumption that subclasses don't override `__eq__`/`__ne__`, and more conservative narrowing from `in` checks and `match` value patterns. Fewer narrowing opportunities; more sound for types with custom equality.

### `strict-generic-narrowing`

Default `false`. When `true`, `isinstance(value, list)` (unspecialized generic) narrows to the top materialization `Top[list[Unknown]]` (iteration yields `object`). When `false` (default), compatible type arguments are preserved — `isinstance(value, list)` narrows `Sequence[int]` to `list[int]`, and `object` to `list[Unknown]`.

## `environment`

### `extra-paths`

Paths taking first priority in module resolution — for modules not installed conventionally (like mypy's `MYPYPATH` or pyright's `stubPath`). Default `[]`.

### `python`

Path to the Python environment/interpreter used to resolve third-party imports: an interpreter (`.venv/bin/python3`), a venv directory (`.venv`), or a `sys.prefix` directory (`/usr`). Usually unnecessary with uv (`VIRTUAL_ENV` is set), an activated Conda env, or a project `.venv`. Default `null` (auto-discovery).

### `python-platform`

Target platform for `sys.platform`-conditional code: `win32`, `darwin`, `android`, `ios`, `linux`, `all`, or a custom string. Default: the current platform.

### `python-version`

Version string `"3.7"`..`"3.15"`. Officially supported: 3.10+ (3.7-3.9 may give false positives/negatives due to missing bundled stubs). If unset: `project.requires-python` minimum → active environment → latest stable supported (3.14 in 0.0.72). PEP 723 scripts use their own `requires-python`.

### `root`

Root paths for first-party module discovery, searched in priority order (first = highest). If unset, ty auto-detects common layouts: `.` plus, if they exist and are not packages, `./src`, `./<project-name>` (when `./<project-name>/<project-name>` exists), and `./python`. PEP 723 scripts have no first-party roots by default (set `root = ["."]` to import local modules).

```toml
[tool.ty.environment]
root = ["./src", "./lib", "./vendor"]
```

### `typeshed`

Custom typeshed directory for stdlib stubs. Default: vendored stubs bundled in the binary.

## `overrides`

Array of file-specific configuration overrides. Multiple overrides can match one file; later ones win; override rules beat global rules for matching files.

```toml
[[tool.ty.overrides]]
include = ["tests/**", "**/test_*.py"]

[tool.ty.overrides.rules]
possibly-unresolved-reference = "warn"
```

Fields:

- `include` — patterns to include (default `["**"]`)
- `exclude` — patterns to exclude (default `[]`); exclude beats include within one override
- `rules` — per-override rule severities
- `analysis` — the same five `analysis` options, scoped to matching files

## `src`

### `include`

Files/directories to check (gitignore-like, anchored; exclude takes precedence). Default: all Python files in the project.

### `exclude`

Patterns to exclude. Default list includes common noise: `**/.bzr/`, `**/.direnv/`, `**/.eggs/`, `**/.git/`, `**/.git-rewrite/`, `**/.hg/`, `**/.mypy_cache/`, and similar (`.venv`, `build`, `dist`, `node_modules`, etc.). Remove a default with a negated pattern: `exclude = ["!**/build/"]`.

### `exclude-scripts`

Exclude PEP 723 inline-metadata scripts unless passed explicitly. Default `false` (the CLI flag `--exclude-scripts` sets this).

### `respect-ignore-files`

Respect `.gitignore`/`.ignore` exclusions. Default `true`.

## `terminal`

### `error-on-warning`

Exit 1 when all diagnostics are warning-severity. **Default `true` in 0.0.72** — set `false` for a CI gate that tolerates warnings.

### `output-format`

`full` (default, with context and hints) | `concise` | `github` | `gitlab` | `junit`.
