# Ruff Integrations (0.16.3)

Table of contents

- [pre-commit](#pre-commit)
- [GitHub Actions](#github-actions)
- [GitLab CI/CD](#gitlab-cicd)
- [Docker](#docker)
- [Editors and LSP](#editors-and-lsp)
- [nbQA](#nbqa)
- [mdformat](#mdformat)

## pre-commit

Via the official [`ruff-pre-commit`](https://github.com/astral-sh/ruff-pre-commit)
repository — pin `rev` to the Ruff version:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.3
    hooks:
      - id: ruff-check
        args: [--fix]        # apply fixes
      - id: ruff-format
        # to also format Markdown code blocks:
        # types_or: [python, pyi, jupyter, markdown]
```

Note: pre-commit runs each hook on the files it passes explicitly, so use
`--force-exclude` (or a hook `args`) if excluded files must stay excluded
when named directly.

## GitHub Actions

Official action:

```yaml
name: Ruff
on: [push, pull_request]
jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v3
```

Or manually (install + run), which is handy for non-default invocations:

```yaml
- uses: actions/checkout@v4
- name: Install Ruff
  run: pipx install ruff==0.16.3    # or uv tool install ruff==0.16.3
- run: ruff check .
- run: ruff format --check .
```

CI-friendly output: `ruff check --output-format github .` and
`ruff format --check --output-format github .` emit GitHub annotation
comments (also `gitlab`, `junit`, `sarif`, `azure`, …).

## GitLab CI/CD

```yaml
stages: [lint]
ruff-lint:
  stage: lint
  image: ghcr.io/astral-sh/ruff:0.16.3
  script:
    - ruff check .
    - ruff format --check .
```

## Docker

Published as `ghcr.io/astral-sh/ruff`, tagged per release and `latest`:

```shell
docker run -v .:/io --rm ghcr.io/astral-sh/ruff:0.16.3 check
docker run -v .:/io --rm ghcr.io/astral-sh/ruff:0.16.3 format --check
# Podman on SELinux: add :Z to the volume mount (-v .:/io:Z)
```

## Editors and LSP

- **VS Code** — first-party extension (`charliermarsh.ruff` / `astral-sh.ruff`);
  install Ruff separately, set `ruff.path` if needed.
- **LSP** — `ruff server` runs Ruff's language server for editors with LSP
  support (diagnostics, go-to-definition in rules/settings, quick fixes).
- **Notebook code actions** — Ruff does not support `source.organizeImports`
  / `source.fixAll` on Jupyter notebooks (it needs the full notebook view;
  per-cell actions duplicate edits). Use the `notebook.`-prefixed variants:
  `notebook.source.organizeImports`, `notebook.source.fixAll`.
- Other editors: see the "Editors" section of the ruff docs
  (docs.astral.sh/ruff/editors).

## nbQA

For running Ruff over notebooks without Ruff's native notebook support
(legacy workflow; native support has been the default since 0.6.0):

```shell
nbqa ruff Untitled.ipynb
```

## mdformat

If a project already formats Markdown with `mdformat`, either let
`ruff format` handle code blocks and skip `mdformat` for `.md` Python fences,
or keep `mdformat` for prose and disable Ruff's Markdown handling with
`extend-exclude = ["*.md"]`. The two tools do not coordinate, so pick one
owner of `.md` files to avoid churn.
