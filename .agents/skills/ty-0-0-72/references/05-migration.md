# Migration from mypy / Pyright (ty 0.0.72)

Source: https://docs.astral.sh/ty/coming-from-mypy-or-pyright/

- [Migration tips](#migration-tips)
- [Stricter checking with ty](#stricter-checking-with-ty) — recommended `--strict` approximations
- [Mapping pyright/mypy rules to ty/Ruff rules](#mapping-pyrightmypy-rules-to-tyruff-rules) — full rule mapping table

This guide helps you migrate a project from
[mypy](https://mypy.readthedocs.io/en/stable/) or
[pyright](https://microsoft.github.io/pyright/) to ty.

## Migration tips

- mypy disables an error code with `# type: ignore[code]`; pyright suppresses a single line with
    `# pyright: ignore[reportXyz]`; ty's equivalent is `# ty: ignore[rule]`.
    See [this page](https://docs.astral.sh/ty/suppression/) for more information about suppression comments.
- mypy's `disable_error_code` and pyright's `reportXyz = "none"` both correspond to setting
    `<rule> = "ignore"` under `[tool.ty.rules]`. See [this section](https://docs.astral.sh/ty/reference/configuration/#rules) for
    details.
- Severities in ty are `ignore`, `warn`, `error`. Pyright's `"information"` and `"hint"` levels have
    no direct ty equivalent — use `warn` for both.
- If you are looking for the equivalent of `disallow_untyped_defs` / `no-untyped-def` (mypy) or `reportMissingParameterType`,
    `reportUnknownParameterType` (pyright), check out this
    [FAQ entry](https://docs.astral.sh/ty/reference/typing-faq/).
- Unlike mypy, ty checks the bodies of unannotated functions unconditionally, so there is no ty rule
    corresponding to mypy's `check_untyped_defs` setting. The equivalent pyright setting is
    `analyzeUnannotatedFunctions = true`.

## Stricter checking with ty

For both mypy and pyright, "strict" mode enables several error codes that are otherwise disabled by
default, but also makes fundamental changes to the way type inference and type checking works.
Mypy's strict mode includes `--check-untyped-defs`, for example, without which unannotated
functions are left unchecked; pyright's strict mode includes `strictListInference`, without which
`[1, "foo"]` will be inferred as having type `list[Unknown]` rather than `list[int | str]` or
similar.

ty's default mode is currently stricter by default than either mypy or pyright in many ways. ty
does not have flags such as `--check-untyped-defs` or `strictListInference`, because these are
ty's default behaviour and are not currently configurable. Meanwhile, nearly all ty rules are
enabled by default, and the ones that are disabled by default are usually in that category because
they are either very opinionated or have many false positives.

### Recommended configuration

To enable all ty rules at once with the `error` severity, you can simply use `--error=all`, but we
wouldn't recommend it. Instead, you can currently approximate something similar to the `--strict`
mode of other type checkers with the following configuration:

```toml
[tool.ty.rules]
missing-type-argument = "error"
possibly-unresolved-reference = "warn"
unsound-return-statement = "error"

[tool.ruff.lint]
extend-select = ["ANN", "PYI"]
preview = true
```

This configuration:

- Enables ty's disabled-by-default [`missing-type-argument`](https://docs.astral.sh/ty/reference/rules/#missing-type-argument), [`possibly-unresolved-reference`](https://docs.astral.sh/ty/reference/rules/#possibly-unresolved-reference), and [`unsound-return-statement`](https://docs.astral.sh/ty/reference/rules/#unsound-return-statement) rules
- Extends Ruff's default rules with the [`ANN`](https://docs.astral.sh/ruff/rules/#flake8-annotations-ann) and [`PYI`](https://docs.astral.sh/ruff/rules/#flake8-pyi-pyi) rule categories, both of which are focussed on type-annotating your code more effectively
- Enables Ruff's preview mode so that `PYI033` also checks `.py` files

An even stricter configuration -- that goes beyond what mypy and pyright check for in their default
`--strict` mode in several respects -- might look like this:

```toml
[tool.ty.rules]
blanket-ignore-comment = "error"
missing-type-argument = "error"
possibly-unresolved-reference = "warn"
unsound-return-statement = "error"
unsound-yield = "error"
unsupported-dynamic-base = "warn"

# NOTE: the following rules are known to have a significant number of false positives,
# which is mostly unavoidable. Enable them at your own risk!
division-by-zero = "warn"
possibly-missing-attribute = "warn"
possibly-missing-import = "warn"

[tool.ty.analysis]
strict-literal-narrowing = true
strict-generic-narrowing = true

[tool.ruff.lint]
extend-select = ["ANN", "PYI", "PGH003"]
preview = true
```

Note that several checks in mypy and pyright are not yet implemented in ty. See the rule mapping
table below for more details.

## Mapping pyright/mypy rules to ty/Ruff rules

### How to read this table

- **ty or Ruff rule**: the canonical name, as listed in [Rules](https://docs.astral.sh/ty/reference/rules/) if it is a ty
    rule. Configure ty rules under `[tool.ty.rules]`. Where Ruff provides equivalent coverage for a
    check that has no ty rule, the relevant Ruff rule or rule group is linked instead.
- **Mypy error code**: the value passed to `# type: ignore[<code>]` or `disable_error_code`. Some ty
    rules surface as one of mypy's catch-all codes (`misc`, `assignment`, `valid-type`); these
    mappings are deliberately broad.
- **Pyright diagnostic**: the `report*` setting in `pyrightconfig.json` or `[tool.pyright]`.

A blank cell means no direct equivalent exists in that checker (the diagnostic is either not
emitted, or is folded into a broader category that already appears for another ty rule).

### Rules

| ty or Ruff rule                                                                                                              | Mypy error code                                                                                                                | Pyright or basedpyright diagnostic                                                                                       |
| ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| [`call-abstract-method`](https://docs.astral.sh/ty/reference/rules/#call-abstract-method)                                                                            |                                                                                                                                | `reportAbstractUsage`                                                                             |
| [`call-non-callable`](https://docs.astral.sh/ty/reference/rules/#call-non-callable)                                                                                  | `operator`                                                                                                    | `reportCallIssue`                                                                                     |
| [`conflicting-declarations`](https://docs.astral.sh/ty/reference/rules/#conflicting-declarations)                                                                    | `no-redef`                                                                                                    | `reportRedeclaration`                                                                             |
| [`conflicting-metaclass`](https://docs.astral.sh/ty/reference/rules/#conflicting-metaclass)                                                                          | `metaclass`                                                                                                  | `reportGeneralTypeIssues`                                                                     |
| [`cyclic-class-definition`](https://docs.astral.sh/ty/reference/rules/#cyclic-class-definition)                                                                      | `misc`                                                                                                            | `reportGeneralTypeIssues`                                                                     |
| [`deprecated`](https://docs.astral.sh/ty/reference/rules/#deprecated)                                                                                                | `deprecated`                                                                                                | `reportDeprecated`                                                                                   |
| [`division-by-zero`](https://docs.astral.sh/ty/reference/rules/#division-by-zero)                                                                                    |                                                                                                                                |                                                                                                                          |
| [`duplicate-base`](https://docs.astral.sh/ty/reference/rules/#duplicate-base)                                                                                        | `misc`                                                                                                            | `reportGeneralTypeIssues`                                                                     |
| [`empty-body`](https://docs.astral.sh/ty/reference/rules/#empty-body)                                                                                                | `empty-body`                                                                                                |                                                                                                                          |
| [`inconsistent-mro`](https://docs.astral.sh/ty/reference/rules/#inconsistent-mro)                                                                                    | `misc`                                                                                                            | `reportGeneralTypeIssues`                                                                     |
| [`index-out-of-bounds`](https://docs.astral.sh/ty/reference/rules/#index-out-of-bounds)                                                                              | `misc`                                                                                                            | `reportGeneralTypeIssues`                                                                     |
| [`invalid-argument-type`](https://docs.astral.sh/ty/reference/rules/#invalid-argument-type)                                                                          | `arg-type` ; `index` ; `type-var` ; `typeddict-item` | `reportArgumentType` ; `reportAssignmentType`                             |
| [`invalid-assignment`](https://docs.astral.sh/ty/reference/rules/#invalid-assignment)                                                                                | `assignment`                                                                                                | `reportAssignmentType`                                                                           |
| [`invalid-attribute-access`](https://docs.astral.sh/ty/reference/rules/#invalid-attribute-access)                                                                    | `misc`                                                                                                            | `reportAttributeAccessIssue`                                                               |
| [`invalid-await`](https://docs.astral.sh/ty/reference/rules/#invalid-await)                                                                                          | `misc`                                                                                                            | `reportGeneralTypeIssues`                                                                     |
| [`invalid-base`](https://docs.astral.sh/ty/reference/rules/#invalid-base)                                                                                            | `valid-type`                                                                                                | `reportGeneralTypeIssues`                                                                     |
| [`invalid-context-manager`](https://docs.astral.sh/ty/reference/rules/#invalid-context-manager)                                                                      | `misc` ; `attr-defined`                                                                     | `reportGeneralTypeIssues`                                                                     |
| [`invalid-exception-caught`](https://docs.astral.sh/ty/reference/rules/#invalid-exception-caught)                                                                    | `misc`                                                                                                            | `reportGeneralTypeIssues`                                                                     |
| [`invalid-key`](https://docs.astral.sh/ty/reference/rules/#invalid-key)                                                                                              | `typeddict-item` ; `typeddict-unknown-key`                               | `reportAssignmentType`                                                                           |
| [`invalid-metaclass`](https://docs.astral.sh/ty/reference/rules/#invalid-metaclass)                                                                                  | `metaclass`                                                                                                  |                                                                                                                          |
| [`invalid-method-override`](https://docs.astral.sh/ty/reference/rules/#invalid-method-override)                                                                      | `override`                                                                                                    | `reportIncompatibleMethodOverride`                                                   |
| [`invalid-overload`](https://docs.astral.sh/ty/reference/rules/#invalid-overload)                                                                                    | `no-overload-impl`                                                                                    | `reportNoOverloadImplementation`                                                       |
| [`invalid-parameter-default`](https://docs.astral.sh/ty/reference/rules/#invalid-parameter-default)                                                                  | `assignment`                                                                                                | `reportArgumentType`                                                                               |
| [`invalid-raise`](https://docs.astral.sh/ty/reference/rules/#invalid-raise)                                                                                          | `misc`                                                                                                            | `reportGeneralTypeIssues`                                                                     |
| [`invalid-return-type`](https://docs.astral.sh/ty/reference/rules/#invalid-return-type)                                                                              | `return-value`                                                                                            | `reportReturnType`                                                                                   |
| [`invalid-type-arguments`](https://docs.astral.sh/ty/reference/rules/#invalid-type-arguments)                                                                        | `misc` ; `type-var`                                                                             | `reportInvalidTypeArguments`                                                               |
| [`invalid-type-form`](https://docs.astral.sh/ty/reference/rules/#invalid-type-form)                                                                                  | `valid-type`                                                                                                | `reportInvalidTypeForm`                                                                         |
| [`missing-argument`](https://docs.astral.sh/ty/reference/rules/#missing-argument)                                                                                    | `call-arg`                                                                                                    | `reportCallIssue`                                                                                     |
| [`missing-override-decorator`](https://docs.astral.sh/ty/reference/rules/#missing-override-decorator)                                                                | `explicit-override`                                                                                  | `reportImplicitOverride`                                                                       |
| [`missing-type-argument`](https://docs.astral.sh/ty/reference/rules/#missing-type-argument)                                                                          | `type-arg`                                                                                                    | `reportMissingTypeArgument`                                                                 |
| [`missing-typed-dict-key`](https://docs.astral.sh/ty/reference/rules/#missing-typed-dict-key)                                                                        | `typeddict-item`                                                                                        | `reportAssignmentType`                                                                           |
| [`no-matching-overload`](https://docs.astral.sh/ty/reference/rules/#no-matching-overload)                                                                            | `call-overload`                                                                                          | `reportCallIssue`                                                                                     |
| [`not-iterable`](https://docs.astral.sh/ty/reference/rules/#not-iterable)                                                                                            | `misc` ; `attr-defined`                                                                     | `reportGeneralTypeIssues`                                                                     |
| [`not-subscriptable`](https://docs.astral.sh/ty/reference/rules/#not-subscriptable)                                                                                  | `index`                                                                                                          | `reportIndexIssue`                                                                                   |
| [`parameter-already-assigned`](https://docs.astral.sh/ty/reference/rules/#parameter-already-assigned)                                                                | `misc` ; `call-arg`                                                                             | `reportCallIssue`                                                                                     |
| [`possibly-missing-attribute`](https://docs.astral.sh/ty/reference/rules/#possibly-missing-attribute)                                                                |                                                                                                                                |                                                                                                                          |
| [`possibly-unresolved-reference`](https://docs.astral.sh/ty/reference/rules/#possibly-unresolved-reference)                                                          | `possibly-undefined`                                                                                | `reportPossiblyUnboundVariable`                                                         |
| [`redundant-cast`](https://docs.astral.sh/ty/reference/rules/#redundant-cast)                                                                                        | `redundant-cast`                                                                                        | `reportUnnecessaryCast`                                                                         |
| [`too-many-positional-arguments`](https://docs.astral.sh/ty/reference/rules/#too-many-positional-arguments)                                                          | `call-arg`                                                                                                    | `reportCallIssue`                                                                                     |
| [`type-assertion-failure`](https://docs.astral.sh/ty/reference/rules/#type-assertion-failure)                                                                        | `assert-type`                                                                                              | `reportAssertTypeFailure`                                                                     |
| [`undefined-reveal`](https://docs.astral.sh/ty/reference/rules/#undefined-reveal)                                                                                    | `unimported-reveal`                                                                                  |                                                                                                                          |
| [`unknown-argument`](https://docs.astral.sh/ty/reference/rules/#unknown-argument)                                                                                    | `call-arg`                                                                                                    | `reportCallIssue`                                                                                     |
| [`unresolved-attribute`](https://docs.astral.sh/ty/reference/rules/#unresolved-attribute)                                                                            | `attr-defined` ; `union-attr`                                                         | `reportAttributeAccessIssue` ; `reportOptionalMemberAccess` |
| [`unresolved-import`](https://docs.astral.sh/ty/reference/rules/#unresolved-import)                                                                                  | `import-not-found`                                                                                    | `reportMissingImports`                                                                           |
| [`unresolved-reference`](https://docs.astral.sh/ty/reference/rules/#unresolved-reference)                                                                            | `name-defined`                                                                                            | `reportUndefinedVariable`                                                                     |
| [`unsound-return-statement`](https://docs.astral.sh/ty/reference/rules/#unsound-return-statement)                                                                    | `no-any-return`                                                                                          |                                                                                                                          |
| [`unsound-yield`](https://docs.astral.sh/ty/reference/rules/#unsound-yield)                                                                                          |                                                                                                                                |                                                                                                                          |
| [`unsupported-operator`](https://docs.astral.sh/ty/reference/rules/#unsupported-operator)                                                                            | `operator`                                                                                                    | `reportOperatorIssue`                                                                             |
| [`unused-awaitable`](https://docs.astral.sh/ty/reference/rules/#unused-awaitable)                                                                                    | `unused-coroutine` ; `unused-awaitable`                                     | `reportUnusedCoroutine`                                                                         |
| [`unused-ignore-comment`](https://docs.astral.sh/ty/reference/rules/#unused-ignore-comment)                                                                          | `unused-ignore`                                                                                          | `reportUnnecessaryTypeIgnoreComment`                                               |
| `blanket-ignore-comment`, Ruff `PGH003`                                          | `ignore-without-code`                                                                              | `reportIgnoreCommentWithoutRule` (basedpyright only)                                   |
| None yet (tracked in Ruff #10137)                                                                              |                                                                                                                                | `reportConstantRedefinition`                                                               |
| Ruff `F811` ; Ruff `I001`                                                                         |                                                                                                                                | `reportDuplicateImport`                                                                         |
| None yet (tracked in #3647)                                                                                       |                                                                                                                                | `reportImportCycles`                                                                               |
| None yet                                                                                                                     |                                                                                                                                | `reportIncompleteStub`                                                                           |
| None yet (tracked in #3651)                                                                                       |                                                                                                                                | `reportInconsistentConstructor`                                                         |
| Ruff `W605`                                                                                                     |                                                                                                                                | `reportInvalidStringEscapeSequence`                                                 |
| Ruff `PYI010` ; Ruff `PYI017` ; Ruff `PYI048` ; Ruff `PYI052` |                                                                                                                                | `reportInvalidStubStatement`                                                               |
| None yet (tracked in #1017, #3636, #3637)                                                   | `type-var`                                                                                                    | `reportInvalidTypeVarUse`                                                                     |
| None yet (tracked in #1060)                                                                                       | `exhaustive-match`                                                                                    | `reportMatchNotExhaustive`                                                                   |
| None yet (tracked in #1577)                                                                                       |                                                                                                                                | `reportMissingModuleSource`                                                                 |
| None yet (tracked in #3652)                                                                                       |                                                                                                                                | `reportMissingSuperCall`                                                                       |
| None yet (tracked in #3638)                                                                                       | `import-untyped`                                                                                        | `reportMissingTypeStubs`                                                                       |
| None yet (tracked in #103)                                                                                         | `overload-overlap`                                                                                    | `reportOverlappingOverload`                                                                 |
| None yet (tracked in #200)                                                                                         | `attr-defined` ; (extended by `--no-implicit-reexport`)                     | `reportPrivateImportUsage`                                                                   |
| None yet (tracked in #3633)                                                                                       |                                                                                                                                | `reportPropertyTypeMismatch`                                                               |
| Ruff `N804` ; Ruff `N805`                                                                         |                                                                                                                                | `reportSelfClsParameterName`                                                               |
| Ruff `PYI033` (preview only)                                                                                  |                                                                                                                                | `reportTypeCommentUsage`                                                                       |
| None yet (tracked in #2810)                                                                                       |                                                                                                                                | `reportTypedDictNotRequiredAccess`                                                   |
| None yet (tracked in #2954)                                                                                       |                                                                                                                                | `reportUninitializedInstanceVariable`                                             |
| None yet (tracked in #576)                                                                                         | `comparison-overlap`                                                                                | `reportUnnecessaryComparison` ; `reportUnnecessaryContains` |
| None yet (tracked in #1948)                                                                                       | `unreachable`                                                                                              | `reportUnreachable`                                                                                 |
| Ruff `F822` ; Ruff `PLE0604` ; Ruff `PLE0605` ; Ruff `PYI056` |                                                                                                                                | `reportUnsupportedDunderAll`                                                               |
| Ruff `PYI024`                                                                                                 |                                                                                                                                | `reportUntypedNamedTuple`                                                                     |
| Ruff `B018`                                                                                                     |                                                                                                                                | `reportUnusedExpression`                                                                       |
| Ruff `F403`                                                                                                     |                                                                                                                                | `reportWildcardImportFromLibrary`                                                     |
| None yet                                                                                                                     | `no-untyped-call`                                                                                      |                                                                                                                          |
| Ruff `ANN` rules                                                                                                 | `no-untyped-def`                                                                                        | `reportMissingParameterType` ; `reportUnknownParameterType` |
| None yet                                                                                                                     | `untyped-decorator`                                                                                  | `reportUntypedFunctionDecorator`                                                       |

The full list of ty rules — including those without a direct equivalent above — is in
[Rules](https://docs.astral.sh/ty/reference/rules/). Contributions to extend this mapping are welcome via pull request to the
[`ty` repository](https://github.com/astral-sh/ty); see issue
[#2111](https://github.com/astral-sh/ty/issues/2111) for context.


Note on the "even stricter" config above: the example sets `strict-literal-narrowing = true`, but
`strict-literal-narrowing` does not appear in the 0.0.72 configuration reference (the `analysis`
section documents `strict-equality-semantics` and `strict-generic-narrowing`). If ty rejects the
key as invalid configuration (exit code 2), remove that line.
