# Rules (ty 0.0.72)

Source: https://docs.astral.sh/ty/reference/rules/

- [All rules and default levels](#all-rules-and-default-levels) — 126-rule table
- [Notable rules disabled by default](#notable-rules-disabled-by-default)

## All rules and default levels

126 rules: 93 default to `error`, 23 to `warn`, 10 to `ignore`. Levels are configurable per rule (and via `all`) through the CLI (`--error`, `--warn`, `--ignore`) or `[tool.ty.rules]`. Query any rule's full documentation, examples, and related issues with `ty explain rule <name>` (omit the name for all rules; `--output-format json` for machine-readable output).

| Rule | Default level | What it checks |
|---|---|---|
| `abstract-and-final-method` | error | Checks for methods decorated with both `@abstractmethod` and `@final`. |
| `abstract-method-in-final-class` | error | Checks for `@final` classes that have unimplemented abstract methods. |
| `ambiguous-protocol-member` | warn | Checks for protocol classes with members that will lead to ambiguous interfaces. |
| `assert-type-unspellable-subtype` | error | Checks for `assert_type()` calls where the actual type is an unspellable subtype of the asserted type. |
| `blanket-ignore-comment` | ignore | Checks for `ty: ignore` comments that don't specify which rules to ignore. |
| `call-abstract-method` | error | Checks for calls to abstract `@classmethod`s or `@staticmethod`s with "trivial bodies" when accessed on the class object itself. |
| `call-non-callable` | error | Checks for calls to non-callable objects. |
| `call-top-callable` | error | Checks for calls to objects typed as `Top[Callable[..., T]]` (the infinite union of all callable types with return type `T`). |
| `conflicting-declarations` | error | Checks whether a variable has been declared as two conflicting types. |
| `conflicting-metaclass` | error | Checks for class definitions where the metaclass of the class being created would not be a subclass of the metaclasses of all the class's bases. |
| `cyclic-class-definition` | error | Checks for class definitions in stub files that inherit (directly or indirectly) from themselves. |
| `cyclic-type-alias-definition` | error | Checks for type alias definitions that (directly or mutually) refer to themselves. |
| `dataclass-field-order` | error | Checks for dataclass definitions where required fields are defined after fields with default values. |
| `deprecated` | warn | Checks for uses of deprecated items |
| `division-by-zero` | ignore | It detects division by zero. |
| `duplicate-base` | error | Checks for class definitions with duplicate bases. |
| `duplicate-kw-only` | error | Checks for dataclass definitions with more than one field annotated with `KW_ONLY`. |
| `empty-body` | error | Detects functions with empty bodies that have a non-`None` return type annotation. |
| `escape-character-in-forward-annotation` | error | Checks for forward annotations that contain escape characters. |
| `experimental-syntax` | warn | Checks for experimental syntax that is not part of the Python typing specification. |
| `final-on-non-method` | error | Checks for `@final` decorators applied to non-method functions. |
| `final-without-value` | error | Checks for `Final` symbols that are declared without a value and are never assigned a value in their scope. |
| `ignore-comment-unknown-rule` | warn | Checks for `ty: ignore[code]` or `type: ignore[ty:code]` comments where `code` isn't a known lint rule. |
| `implicit-concatenated-string-type-annotation` | error | Checks for implicit concatenated strings in type annotation positions. |
| `inconsistent-mro` | error | Checks for classes with an inconsistent [method resolution order] (MRO). |
| `index-out-of-bounds` | error | Checks for attempts to use an out of bounds index to get an item from a container. |
| `ineffective-final` | warn | Checks for calls to `final()` that type checkers cannot interpret. |
| `instance-layout-conflict` | error | Checks for classes definitions which will fail at runtime due to "instance memory layout conflicts". |
| `invalid-argument-type` | error | Detects call arguments whose type is not assignable to the corresponding typed parameter. |
| `invalid-assignment` | error | Checks for assignments where the type of the value is not [assignable to] the type of the assignee. |
| `invalid-attribute-access` | error | Checks for assignments to class variables from instances and assignments to instance-only attributes from their class. |
| `invalid-attribute-override` | error | Detects attribute overrides that change whether an inherited attribute is a class variable or an instance variable. |
| `invalid-await` | error | Checks for `await` being used with types that are not [Awaitable][awaitable-abc]. |
| `invalid-base` | error | Checks for class definitions that have bases which are not instances of `type`. |
| `invalid-context-manager` | error | Checks for expressions used in `with` statements that do not implement the context manager protocol. |
| `invalid-dataclass` | error | Checks for invalid applications of the `@dataclass` decorator. |
| `invalid-dataclass-override` | error | Checks for dataclass definitions that have both `frozen=True` and a custom `__setattr__` or `__delattr__` method defined. |
| `invalid-declaration` | error | Checks for declarations where the inferred type of an existing symbol is not [assignable to] its post-hoc declared type. |
| `invalid-enum-member-annotation` | warn | Checks for enum members that have explicit type annotations. |
| `invalid-exception-caught` | error | Checks for exception handlers that catch non-exception classes. |
| `invalid-explicit-override` | error | Checks for methods that are decorated with `@override` but do not override any method in a superclass. |
| `invalid-frozen-dataclass-subclass` | error | Checks for dataclasses with invalid frozen inheritance: |
| `invalid-generic-class` | error | Checks for the creation of invalid generic classes |
| `invalid-generic-enum` | error | Checks for enum classes that are also generic. |
| `invalid-ignore-comment` | warn | Checks for `type: ignore` and `ty: ignore` comments that are syntactically incorrect. |
| `invalid-key` | error | Checks for subscript accesses with invalid keys and `TypedDict` construction with an unknown key. |
| `invalid-legacy-positional-parameter` | warn | Checks for parameters that appear to be attempting to use the legacy convention to specify that a parameter is positional-only, but do so incorrectly. |
| `invalid-legacy-type-variable` | error | Checks for the creation of invalid legacy `TypeVar`s |
| `invalid-match-pattern` | error | Checks for invalid match patterns. |
| `invalid-metaclass` | error | Checks for arguments to `metaclass=` that are invalid. |
| `invalid-method-override` | error | Detects method overrides that violate the [Liskov Substitution Principle][liskov-substitution-principle] ("LSP"). |
| `invalid-module-getattr-call` | error | Checks for imports that fail when calling a module-level `__getattr__` function. |
| `invalid-named-tuple` | error | Checks for invalidly defined `NamedTuple` classes. |
| `invalid-named-tuple-override` | warn | Checks for subclass members that override inherited `NamedTuple` fields. |
| `invalid-newtype` | error | Checks for the creation of invalid `NewType`s |
| `invalid-overload` | error | Checks for various invalid `@overload` usages. |
| `invalid-parameter-default` | error | Checks for default values that can't be assigned to the parameter's annotated type. |
| `invalid-paramspec` | error | Checks for the creation of invalid `ParamSpec`s |
| `invalid-protocol` | error | Checks for protocol classes that will raise `TypeError` at runtime. |
| `invalid-raise` | error | Checks for `raise` statements that raise non-exceptions or use invalid causes for their raised exceptions. |
| `invalid-return-type` | error | Detects returned values that can't be assigned to the function's annotated return type. |
| `invalid-super-argument` | error | Detects `super()` calls where: |
| `invalid-syntax-in-forward-annotation` | error | Checks for string-literal annotations where the string cannot be parsed as a Python expression. |
| `invalid-total-ordering` | error | Checks for classes decorated with `@functools.total_ordering` that don't define any ordering method (`__lt__`, `__le__`, `__gt__`, or `__ge__`). |
| `invalid-type-alias-type` | error | Checks for the creation of invalid `TypeAliasType`s |
| `invalid-type-arguments` | error | Checks for invalid type arguments in explicit type specialization. |
| `invalid-type-checking-constant` | error | Checks for a value other than `False` assigned to the `TYPE_CHECKING` variable, or an annotation not assignable from `bool`. |
| `invalid-type-form` | error | Checks for expressions that are used as [type expressions] but cannot validly be interpreted as such. |
| `invalid-type-guard-definition` | error | Checks for type guard functions without a first non-self-like non-keyword-only non-variadic parameter. |
| `invalid-type-variable-bound` | error | Checks for [type variables][type variable] whose bounds reference type variables. |
| `invalid-type-variable-constraints` | error | Checks for constrained [type variables] with only one constraint, or that those constraints reference type variables. |
| `invalid-type-variable-default` | error | Checks for [type variables] whose default type is not compatible with the type variable's bound or constraints. |
| `invalid-typed-dict-field` | error | Detects invalid `TypedDict` field declarations. |
| `invalid-typed-dict-header` | error | Detects errors in `TypedDict` class headers, such as unexpected arguments or invalid base classes. |
| `invalid-typed-dict-statement` | error | Detects statements other than annotated declarations in `TypedDict` class bodies. |
| `invalid-yield` | error | Detects `yield` and `yield from` expressions where the "yield" or "send" type is incompatible with the generator function's annotated return type. |
| `isinstance-against-protocol` | error | Reports invalid runtime checks against `Protocol` classes. This includes explicit calls `isinstance()`/`issubclass()` against non-runtime-checkable protocols, `issubclass()` calls against protocols that have non-method members, and implicit `isinstance()` checks against non-runtime-checkable protocols via pattern matching. |
| `isinstance-against-typed-dict` | error | Reports runtime checks against `TypedDict` classes. This includes explicit calls to `isinstance()`/`issubclass()` and implicit checks performed by `match` class patterns. |
| `mismatched-type-name` | warn | Checks for functional typing definitions whose declared name does not match the variable they are assigned to. |
| `missing-argument` | error | Checks for missing required arguments in a call. |
| `missing-override-decorator` | ignore | Checks for methods that override a method or attribute in a superclass but are not decorated with `@override`. |
| `missing-type-argument` | ignore | Checks for generic types used without type parameters in type expressions. |
| `missing-typed-dict-key` | error | Detects missing required keys in `TypedDict` constructor calls. |
| `no-matching-overload` | error | Checks for calls to an overloaded function that do not match any of the overloads. |
| `non-callable-init-subclass` | error | Checks for class definitions that will fail due to non-callable `__init_subclass__` methods. |
| `not-iterable` | error | Checks for objects that are not iterable but are used in a context that requires them to be. |
| `not-subscriptable` | error | Checks for subscripting objects that do not support subscripting. |
| `override-of-final-method` | error | Checks for methods on subclasses that override superclass methods decorated with `@final`. |
| `override-of-final-variable` | error | Checks for class variables on subclasses that override a superclass variable that has been declared as `Final`. |
| `parameter-already-assigned` | error | Checks for calls which provide more than one argument for a single parameter. |
| `positional-only-parameter-as-kwarg` | error | Checks for keyword arguments in calls that match positional-only parameters of the callable. |
| `possibly-missing-attribute` | ignore | Checks for possibly missing attributes. |
| `possibly-missing-implicit-call` | warn | Checks for implicit calls to possibly missing methods. |
| `possibly-missing-import` | ignore | Checks for imports of symbols that may be missing. |
| `possibly-missing-submodule` | warn | Checks for accesses of submodules that might not've been imported. |
| `possibly-unresolved-reference` | ignore | Checks for references to names that are possibly not defined. |
| `pydantic-discarded-extra-argument` | warn | Checks for extra keyword arguments that Pydantic silently discards when a model uses `extra="ignore"`, either implicitly or explicitly. |
| `raw-string-type-annotation` | error | Checks for raw-strings in type annotation positions. |
| `redundant-cast` | warn | Detects redundant `cast` calls where the value already has the target type. |
| `redundant-final-classvar` | warn | Checks for redundant combinations of the `ClassVar` and `Final` type qualifiers. |
| `shadowed-type-variable` | error | Checks for type variables in nested generic classes or functions that shadow type variables from an enclosing scope. |
| `static-assert-error` | error | Makes sure that the argument of `static_assert` is statically known to be true. |
| `subclass-of-dataclass-with-order` | warn | Checks for classes that inherit from a dataclass with `order=True`. |
| `subclass-of-final-class` | error | Checks for classes that subclass final classes. |
| `super-call-in-named-tuple-method` | error | Checks for calls to `super()` inside methods of `NamedTuple` classes. |
| `too-many-positional-arguments` | error | Checks for calls that pass more positional arguments than the callable can accept. |
| `type-assertion-failure` | error | Checks for `assert_type()` and `assert_never()` calls where the actual type is not the same as the asserted type. |
| `unavailable-implicit-super-arguments` | error | Detects invalid `super()` calls where implicit arguments like the enclosing class or first method argument are unavailable. |
| `unbound-type-variable` | error | Checks for type variables that are used in a scope where they are not bound to any enclosing generic context. |
| `undefined-reveal` | warn | Checks for calls to `reveal_type` without importing it. |
| `unknown-argument` | error | Checks for keyword arguments in calls that don't match any parameter of the callable. |
| `unresolved-attribute` | error | Checks for unresolved attributes. |
| `unresolved-global` | warn | Detects variables declared as `global` in an inner scope that have no explicit bindings or declarations in the global scope. |
| `unresolved-import` | error | Checks for import statements for which the module cannot be resolved. |
| `unresolved-reference` | error | Checks for references to names that are not defined. |
| `unsound-return-statement` | ignore | Detects `return` statements that unsoundly return a type that is not a [subtype] of the function's annotated return type. |
| `unsound-yield` | ignore | Detects `yield` and `yield from` expressions that unsoundly yield a type that is not a [subtype] of the generator function's annotated yield type. |
| `unsupported-base` | warn | Checks for class definitions that have bases which are unsupported by ty. |
| `unsupported-bool-conversion` | error | Checks for bool conversions where the object doesn't correctly implement `__bool__`. |
| `unsupported-dynamic-base` | ignore | Checks for dynamic class definitions (using `type()`) that have bases which are unsupported by ty. |
| `unsupported-operator` | error | Checks for binary expressions, comparisons, and unary expressions where the operands don't support the operator. |
| `unused-awaitable` | warn | Checks for awaitable objects (such as coroutines) used as expression statements without being awaited. |
| `unused-ignore-comment` | warn | Checks for `ty: ignore` directives that are no longer applicable. |
| `unused-type-ignore-comment` | warn | Checks for `type: ignore` directives that are no longer applicable. |
| `useless-overload-body` | warn | Checks for various `@overload`-decorated functions that have non-stub bodies. |
| `zero-stepsize-in-slice` | error | Checks for a step size of zero in slices when the operation is known to fail. |

## Notable rules disabled by default (enable deliberately)

- `blanket-ignore-comment` — flags `ty: ignore` comments without a rule list
- `division-by-zero` — detects division by zero (disabled due to false positives)
- `missing-override-decorator` — methods that should use `@override`
- `missing-type-argument` — generic types used without parameters (like mypy `type-arg` / pyright `reportMissingTypeArgument`)
- `possibly-missing-attribute` / `possibly-missing-import` / `possibly-missing-submodule` / `possibly-unresolved-reference` — possibly-unresolved diagnostics
- `unsound-return-statement` / `unsound-yield` — return/yield of `Unknown` in typed functions
- `unsupported-dynamic-base` — subclasses of `type`
