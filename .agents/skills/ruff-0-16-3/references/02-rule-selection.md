# Ruff Rule Selection (0.16.3)

Table of contents

- [Rule codes](#rule-codes)
- [Selectors](#selectors)
- [`ALL`](#all)
- [Recommended guidelines](#recommended-guidelines)
- [Reconciling multiple sources](#reconciling-multiple-sources)
- [Preview rules](#preview-rules)
- [Fix safety](#fix-safety)
- [Disabling fixes](#disabling-fixes)
- [Exit codes](#exit-codes)
- [Output formats](#output-formats)
- [Useful `ruff check` flags](#useful-ruff-check-flags)

## Rule codes

Ruff mirrors Flake8's rule code system: a one-to-three letter prefix followed
by three digits (e.g. `F401`). The prefix identifies the rule's *source* —
`F` for Pyflakes, `E`/`W` for pycodestyle, `ANN` for flake8-annotations, `B`
for flake8-bugbear, `I` for isort, `UP` for pyupgrade, `D` for pydocstyle,
`PL` for pylint, and so on. `ruff linter` lists every supported upstream
linter and its prefix.

Note some rules reuse codes that differ from the originating plugin. Ruff uses
`TID252` for flake8-tidy-imports' `I252`, avoiding a clash with the isort `I`
prefix.

## Selectors

`lint.select`, `lint.extend-select`, and `lint.ignore` (and their CLI twins
`--select`, `--extend-select`, `--ignore`) accept either a full rule code
(`F401`) or any valid prefix (`F`, `E`, `UP`).

```toml
[tool.ruff.lint]
select = ["E", "F"]   # enable all pycodestyle (E) and Pyflakes (F) rules
ignore = ["F401"]     # …except unused-import
```

`select` defines the *base* set; `extend-select` adds to it; `ignore` removes
from it. Selectors can be repeated (or comma-separated) to combine prefixes.

## `ALL`

`select = ["ALL"]` enables every stable rule. Ruff automatically disables rules
that conflict with the selection — e.g. docstring conventions `D203` and `D211`
represent mutually exclusive styles and one is dropped.

Use `ALL` with care: enabling it means *new* rules are picked up automatically
on every Ruff upgrade. Prefer an explicit `select` for reproducible behavior.

## Recommended guidelines

The official guidance for configuring a rule set:

- Prefer `lint.select` over `lint.extend-select` so the rule set is explicit.
- Use `ALL` with discretion — it silently adopts new rules on upgrades.
- Start small (`select = ["E", "F"]`) and add a category at a time.

A popular, not-too-pedantic starting set:

```toml
[tool.ruff.lint]
select = [
  "E",    # pycodestyle
  "F",    # Pyflakes
  "UP",   # pyupgrade
  "B",    # flake8-bugbear
  "SIM",  # flake8-simplify
  "I",    # isort
]
```

## Reconciling multiple sources

When Ruff must reconcile `select`/`ignore` from several sources (the current
`pyproject.toml`, inherited configs, the CLI), it uses the **highest-priority
`select`** as the basis, then applies `extend-select` and `ignore` adjustments.
Priority order: **CLI options** beat the **current config file**, which beats
**inherited** config files.

Example: config has `select = ["E", "F"]`, `ignore = ["F401"]`.

- `ruff check --select F401` enforces **only** `F401` (the CLI `select`
  replaces the configured base).
- `ruff check --extend-select B` enforces `E`, `F`, `B`, minus `F401`.

In preview mode, selectors also accept a rule's human-readable name (e.g.
`unused-import`) instead of a code.

## Preview rules

A rule marked as *preview* is only selected when preview mode is enabled —
adding it to `extend-select`, its prefix, or `ALL` has no effect on its own.
Enable preview via `--preview`, or `preview = true` (configurable separately
per tool with `lint.preview` / `format.preview`).

By default, enabling preview also enables *every* preview rule matching your
selected prefixes/categories. To opt in per-rule instead, set:

```toml
[tool.ruff.lint]
preview = true
explicit-preview-rules = true
```

…then each preview rule must be selected by its exact code
(e.g. `--select ALL,HYP001`). When preview is enabled, *deprecated* rules are
disabled, and explicitly selecting one is an error.

## Fix safety

Ruff labels each auto-fix **safe** or **unsafe**. Safe fixes preserve runtime
behavior and only drop comments when deleting whole statements. Unsafe fixes
*can* change behavior or remove comments.

`ruff check --fix` applies safe fixes only. To include unsafe fixes, pass
`--unsafe-fixes` or set `unsafe-fixes = true`.

Canonical example: `RUF015` rewrites `list(...)[0]` to `next(iter(...))`. On an
empty collection the raised exception changes from `IndexError` to
`StopIteration`, which can break upstream `except` clauses — so the fix is
unsafe and off by default.

Tune safety per rule with `lint.extend-safe-fixes` (promote) and
`lint.extend-unsafe-fixes` (demote); both accept prefixes:

```toml
[tool.ruff.lint]
extend-safe-fixes = ["F601"]    # treat F601's fix as safe
extend-unsafe-fixes = ["UP034"] # treat UP034's fix as unsafe
```

`unsafe-fixes = false` (or `--no-unsafe-fixes`) silences the hint that unsafe
fixes are available. In `json` output every fix is shown with its
`applicability` field.

## Disabling fixes

Control *which* rules may be fixed, independent of safety:

```toml
[tool.ruff.lint]
fixable = ["ALL"]     # (default) everything fixable when --fix is passed
unfixable = ["F401"]  # …but never auto-remove unused imports
# or whitelist:
fixable = ["F401"]    # only F401
```

CLI twins: `--fixable`, `--unfixable`, `--extend-fixable`.

## Exit codes

`ruff check`:

- `0` — no violations, or all present violations were fixed automatically
- `1` — violations found
- `2` — abnormal termination (invalid config, invalid CLI, internal error)

Modifiers:

- `--exit-zero` — exit `0` even if violations are found (still `2` on error)
- `--exit-non-zero-on-fix` — exit `1` if any violations were *fixed*, even if
  none remain (useful in CI to catch "fixes were applied")

`ruff format` normally exits `0` whether or not files changed.
`--exit-non-zero-on-format` exits `1` when any file was reformatted.
`ruff format --check` exits `0` if nothing would change, `1` if something
would, `2` on error.

## Output formats

`--output-format` accepts: `concise`, `full` (default), `json`, `json-lines`,
`junit`, `grouped`, `github`, `gitlab`, `pylint`, `rdjson`, `azure`, `sarif`.
Since 0.16.0, `ruff format --check` supports the same set (e.g. `github`/
`gitlab` for CI annotations). Override via env `RUFF_OUTPUT_FORMAT`; write
output to a file with `-o`/`--output-file` (or `RUFF_OUTPUT_FILE`).

## Useful `ruff check` flags

- `--fix` / `--fix-only` — apply fixes; `--fix-only` skips reporting leftovers
- `--diff` — print a diff of fixes instead of writing files (implies
  `--fix-only`)
- `--show-fixes` — enumerate fixed violations
- `--watch` (`-w`) — re-lint on change
- `--statistics` — per-rule violation counts
- `--show-settings` — dump resolved settings for a file
- `--show-files` — list the files that would be analyzed
- `--add-noqa` / `--add-ignore` — insert suppression comments on failing lines
- `--ignore-noqa` — ignore `# noqa` comments
- `--target-version pyXXX` — override the target Python version
- `--extension ext:lang` — map an extension to a language
- `-n` / `--no-cache`, `--cache-dir` — cache control
- `--stdin-filename` — name to use when reading from stdin
