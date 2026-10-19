# Ruff Formatter (0.16.3)

Table of contents

- [Philosophy](#philosophy)
- [Configuration](#configuration)
- [Docstring code formatting](#docstring-code-formatting)
- [Markdown code formatting](#markdown-code-formatting)
- [Format suppression](#format-suppression)
- [F-string formatting](#f-string-formatting)
- [Fluent method chains (preview)](#fluent-method-chains-preview)
- [Conflicts with the linter](#conflicts-with-the-linter)
- [Known deviations from Black](#known-deviations-from-black)
- [Sorting imports](#sorting-imports)

## Philosophy

`ruff format` is a drop-in replacement for Black, aimed at performance and a
unified toolchain rather than style innovation. It follows Black's (stable)
code style and emits near-identical output on existing Black-formatted code
(> 99.9% of lines identical on projects like Django and Zulip). It is *not*
meant to be run interchangeably with Black forever — a small number of
conscious deviations exist (below). Black's preview style is tracked under
Ruff's own preview mode.

Configuration is deliberately minimal — there is no option for line wrapping
strategy or similar; Ruff rejects YAPF-style configurability.

## Configuration

```toml
[tool.ruff]
line-length = 100

[tool.ruff.format]
quote-style = "single"             # "double" (default), "single", or "preserve"
indent-style = "tab"               # "space" (default) or "tab"
skip-magic-trailing-comma = false  # respect trailing commas (default)
line-ending = "auto"               # auto, lf, crlf, cr
docstring-code-format = true       # format code examples in docstrings
docstring-code-line-length = "dynamic"  # or a fixed int
preview = false
```

Top-level `line-length` (default 88) and `indent-width` (default 4) apply to
the formatter as well. CLI overrides: `--line-length`. Exit codes: `ruff
format` exits `0` even when it reformats (add `--exit-non-zero-on-format` to
exit `1`), and `ruff format --check` exits `1` if any file *would* change.

## Docstring code formatting

Opt-in via `docstring-code-format = true`. Recognized code examples:

- Python [doctest] format
- CommonMark fenced blocks with info strings `python`, `py`, `python3`, `py3`
  — and fenced blocks *without* an info string (assumed Python)
- reStructuredText literal blocks and `code-block` / `sourcecode` directives

A block is skipped if it does not parse as valid Python or if formatting it
would produce invalid Python. `docstring-code-line-length` defaults to
`dynamic` (the surrounding code's `line-length`); set an integer for a fixed
limit.

## Markdown code formatting

New in 0.16.0: `ruff format` formats Python code blocks in Markdown files by
default.

- Recognized fences: `python`, `py`, `python3`, `py3`, `pyi` (stub style),
  `pycon` (REPL style), plus Quarto-style `{python}`.
- Unparseable blocks are skipped.
- Suppression: HTML comment pairs wrap whole regions —
  `<!-- fmt:off --> … <!-- fmt:on -->` (a lone `off` covers to end of file);
  `<!-- blacken-docs:off -->` / `<!-- blacken-docs:on -->` are also honored.
  Normal `# fmt:` pragmas still work inside blocks.
- Non-`.md` Markdown extensions: map them with `extension = { mdx =
  "markdown" }`; with `ruff-pre-commit` add `types_or: [python, pyi,
  jupyter, markdown]` to the hook.
- To disable Markdown formatting: `extend-exclude = ["*.md"]`.

## Format suppression

Black-compatible pragmas:

- `# fmt: off` / `# fmt: on` — enforced at the **statement level**; they have
  no effect inside an expression:

  ```python
  [
      # fmt: off
      '1',
      # fmt: on
      '2',
  ]  # both entries get formatted; move the pair around the whole statement
  ```

- `# yapf: disable` / `# yapf: enable` — recognized as equivalents.
- `# fmt: skip` — suppresses formatting of a case header, decorator,
  function/class definition, or the preceding statements on the same logical
  line. At the *end of an expression* it has no effect:

  ```python
  a = call(
    [
      '1',  # fmt: skip   # no effect — inside an expression
      '2',
    ],
    b
  )
  a = call([...], b)  # fmt: skip   # whole statement skipped
  ```

## F-string formatting

Stabilized in 0.9.0: unlike Black, Ruff formats the *expression parts* of
f-strings (inside `{...}`).

**Quotes** — the configured quote style is used for expressions unless that
would be invalid for the target version or require more backslash escapes.
Below Python 3.12, nested f-strings alternate quote styles starting from the
outermost; on 3.12+ with `nested-string-quote-style = "preferred"`, the
configured style is reused.

**Line breaks** — an f-string expression is only split across multiple lines
if it *already* contained a line break (a Prettier-like heuristic, since Ruff
can't tell prose from code). To force a split, ensure a newline exists
somewhere inside the `{...}` parts.

## Fluent method chains (preview)

Preview style for long method chains on a fixed object — breaks *before* the
first attribute:

```python
x = (
    df
    .filter(cond)
    .agg(func)
    .merge(other)
)
```

Stable style (and Black) break *after* the preceding call, leaving `df` on
the assignment line.

## Conflicts with the linter

These lint rules conflict with the formatter and should be in `lint.ignore`
when `ruff format` is used (none are in the default set; `ruff format` prints
a warning if any is enabled):

- `W191` (tab-indentation), `E111`, `E114`, `E117` (indentation rules)
- `D203`, `D206`, `D300` (pydocstyle style)
- `Q000`–`Q004` (flake8-quotes)
- `COM812`, `COM819` (trailing commas)
- `ISC002` unless paired with `ISC001` and
  `flake8-implicit-str-concat.allow-multiline = false`

`E501` (line-too-long) is compatible but best-effort: formatted code may still
exceed `line-length` (comments and long strings are never wrapped).

These isort settings are incompatible with the formatter when non-default:
`force-single-line`, `force-wrap-aliases`, `lines-after-imports`,
`lines-between-types`, `split-on-trailing-comma` — remove them.

## Known deviations from Black

Intentional or implementation-driven differences from Black's output
(see the "Known deviations" section of `docs/formatter/black.md` in the 0.16.3
source tree for examples):

- Trailing end-of-line comments
- Pragma comments ignored when computing line width
- Line width vs. line length handling
- Parenthesizing long nested expressions
- Call expressions with a single multiline string argument
- Blank lines at the start of a block
- F-strings (Ruff formats expression parts; Black does not)
- Implicit concatenated strings
- `assert` statements
- `global` / `nonlocal` broken across lines via continuations
- Trailing own-line comments on imports not moved to the next line

Unintentional deviations are tracked in the ruff issue tracker
(`label:formatter`).

## Sorting imports

The formatter does not sort imports. To both sort and format:

```shell
ruff check --select I --fix
ruff format
```

A unified lint+format command is planned (astral-sh/ruff#8232) but does not
exist in 0.16.3.
