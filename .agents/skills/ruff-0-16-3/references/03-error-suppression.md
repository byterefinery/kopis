# Ruff Error Suppression (0.16.3)

Table of contents

- [Configuration-level](#configuration-level)
- [Line-level — `noqa`](#line-level--noqa)
- [Line-level — `ruff: ignore[CODE]`](#line-level--ruff-ignorecode)
- [Block-level — `disable` / `enable`](#block-level--disable--enable)
- [File-level](#file-level)
- [Human-readable rule names (preview)](#human-readable-rule-names-preview)
- [Detecting unused suppressions — RUF100](#detecting-unused-suppressions--ruf100)
- [Inserting suppressions — `--add-noqa` / `--add-ignore`](#inserting-suppressions--add-noqa--add-ignore)
- [isort action comments](#isort-action-comments)

## Configuration-level

To omit a rule everywhere, add it to `lint.ignore` (config or `--ignore`).
To omit it in specific files, use `lint.per-file-ignores` with file-pattern
keys:

```toml
[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["E402"]
"tests/**" = ["S101"]
"*.ipynb" = ["T20"]
```

## Line-level — `noqa`

Flake8-compatible inline suppression at the end of a line:

```python
x = 1  # noqa: F841        # ignore F841 on this line
i = 1  # noqa: E741, F841  # several codes
x = 1  # noqa              # blanket — all violations on the line
```

Case-insensitive matching for `#noqa`. Placement details:

- **Multi-line strings** (docstrings): put the directive after the *closing*
  triple quote; it applies to the entire string:

  ```python
  """Lorem ipsum dolor sit amet.
  """  # noqa: E501
  ```

- **Import blocks**: put it on the *first* line of the block; it covers all
  imports in the block:

  ```python
  import os  # noqa: I001
  import abc
  ```

- A code list ends at the last valid code; codes normally separated by commas
  or whitespace (`F401F841` is parsed with a warning).

## Line-level — `ruff: ignore[CODE]`

The `# ruff: ignore[...]` comment (case-sensitive `#ruff:` prefix) covers a
*logical* line — a whole multi-line statement or suite header — not just one
physical line. Since 0.16.0 it may also trail a line, like `noqa`, or sit on
the line preceding a diagnostic:

```python
# ruff: ignore[ARG001]  # above the header: covers the whole signature
def foo(
    arg1,
    arg2,
):
    pass

# ruff: ignore[E501]  # above: covers the entire list literal
things = [
    "really long string literal ...",
]

import math  # ruff: ignore[F401]   # trailing: suppresses on this line

# ruff: ignore[F401]
import os                          # preceding line: also suppresses
```

Contrast: placed *inside* a multi-line statement (or trailing a physical line
of one), it covers only that single physical line:

```python
def foo(
    arg1,
    # ruff: ignore[ARG001]  # only covers `arg2`
    arg2,
):
    pass
```

Codes are comma-separated, with an optional trailing comma. Ignore comments
can be stacked with other comments and still apply to the next logical line.

## Block-level — `disable` / `enable`

Suppress one or more rules across a range of code with a matching pair
(case-sensitive `#ruff:` prefix):

```python
# ruff: disable[E501]
VALUE_1 = "Lorem ipsum dolor sit amet ..."
VALUE_2 = "Lorem ipsum dolor sit amet ..."
# ruff: enable[E501]
```

Rules:

- `disable` and `enable` must list the **same codes, in the same order**, at
  the same indentation level within a logical block.
- If no matching `enable` is found, Ruff treats it as an **implicit range**
  ending at the logical scope indented less than the starting comment.
  Ruff emits a `RUF104` diagnostic for implicit ranges — close ranges
  explicitly to avoid accidental over-suppression (especially at module
  scope).
- Range suppressions cannot enable or select rules that are not already
  selected by config/CLI; an `enable` only terminates a preceding `disable`
  with identical codes.
- Unlike `noqa`, ranges support no blanket suppression — at least one code is
  required.

## File-level

Any one of these, on its own line, anywhere in the file (prefer the top):

```python
# ruff: noqa                      # ignore all violations in this file
# ruff: noqa: F841                # ignore one rule in this file
# ruff: file-ignore[F401, ARG001] # explicit file-level ignore list
```

Ruff also honors Flake8's `# flake8: noqa` (equivalent to `# ruff: noqa`).
Global `noqa` comments must be on their own line to distinguish them from
line-level `noqa`.

## Human-readable rule names (preview)

In preview mode, `ruff: ignore`, `ruff: file-ignore`, `ruff: disable`, and
`ruff: enable` accept rule *names* (e.g. `unused-import`) instead of codes.
`--add-ignore` likewise emits names in preview and codes on stable.

## Detecting unused suppressions — RUF100

`RUF100` (`unused-noqa`) flags suppression comments that no longer match any
violation — i.e., your `# noqa` list is stale:

```shell
ruff check /path/to/file.py --extend-select RUF100        # report stale ones
ruff check /path/to/file.py --extend-select RUF100 --fix  # remove them
```

`RUF104` is its companion: it flags implicit `disable` ranges without an
explicit `enable`.

## Inserting suppressions — `--add-noqa` / `--add-ignore`

When adopting a new rule on an existing codebase, back-fill suppression
comments on every offending line so only *new* code is enforced going
forward:

```shell
ruff check --select UP035 --add-noqa .      # insert `# noqa: UP035`
ruff check --select UP035 --add-ignore .    # insert `# ruff: ignore[UP035]`
```

Both accept an optional reason suffix (e.g. `--add-noqa=legacy`). Both use
rule codes on stable; `--add-ignore` uses rule names in preview.

## isort action comments

Ruff respects isort's action comments for import sorting:

- `# isort: skip_file` — skip the whole file
- `# isort: on` / `# isort: off` — toggle sorting for a region
- `# isort: skip` — skip the next statement
- `# isort: split` — force a split point

`# ruff:`-prefixed variants (e.g. `# ruff: isort: skip_file`) are equivalent
and make intent explicit. Unlike isort, Ruff does not honor action comments
inside docstrings.
