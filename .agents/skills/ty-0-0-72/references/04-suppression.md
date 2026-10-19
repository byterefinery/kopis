# Suppression (ty 0.0.72)

Source: https://docs.astral.sh/ty/suppression/

To disable a rule entirely (project-wide or per file group), set its level to `ignore` in `[tool.ty.rules]` or an `overrides` entry instead of sprinkling comments.

## `ty: ignore` comments

Suppress a violation inline with `# ty: ignore[<rule>]` at the end of the line:

```py
a = 10 + "test"  # ty: ignore[unsupported-operator]
```

Violations spanning multiple lines: place the comment on the **first or last** line of the violation.

```py
sum_three_numbers(  # ty: ignore[missing-argument]
    3,
    2
)
```

Multiple rules on one line: comma-separated list.

```python
sum_three_numbers("one", 5)  # ty: ignore[missing-argument, invalid-argument-type]
```

Whole file: `# ty: ignore[<rule>]` on its own line before any Python code.

```python
# ty: ignore[invalid-argument-type]

sum_three_numbers(3, 2, "1")
```

Rule names in `[...]` are optional (bare `# ty: ignore` suppresses everything on the line), but always include specific rules to avoid accidentally silencing other errors.

## Standard `type: ignore` comments

ty supports the PEP 484 format:

- `type: ignore` — suppresses all violations on the line
- `type: ignore[ty:<rule>]` — behaves like `ty: ignore[<rule>]`
- Codes **without** a `ty:` prefix are ignored by ty, so one comment can serve multiple checkers:

```python
# Ignore all typing errors on the next line
sum_three_numbers("one", 5)  # type: ignore

# Ignore a mypy code and a ty rule in the same comment
sum_three_numbers("one", 5, 2)  # type: ignore[arg-type, ty:invalid-argument-type]
```

Set `analysis.respect-type-ignore-comments = false` to stop respecting `type: ignore` entirely.

## Multiple suppression comments on one line

Combine with other tools' comments on the same line:

```python
result = calculate()  # ty: ignore[invalid-argument-type]  # fmt: skip
```

## Unused suppression comments

With the `unused-ignore-comment` rule enabled (default `warn`), ty reports unused `ty: ignore` and `type: ignore` comments. Such violations can only be suppressed with `# ty: ignore[unused-ignore-comment]` — not with a bare `# ty: ignore` or `# type: ignore`. Related: `unused-type-ignore-comment` (default `warn`) and `blanket-ignore-comment` (default `ignore`).

## `@no_type_check`

The standard `@no_type_check` decorator suppresses all violations inside a function:

```python
from typing import no_type_check

@no_type_check
def main():
    sum_three_numbers(1, 2)  # no error for the missing argument
```

Decorating a **class** with `@no_type_check` is not supported.
