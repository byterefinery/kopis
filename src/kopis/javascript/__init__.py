"""The ``javascript`` module of kopis (server side).

In the browser under Brython, ``javascript`` is a built-in module
exposing Javascript values and constructors. Under CPython this package
is aliased to the top-level name ``javascript`` (see
:mod:`kopis`) so unified code can ``import javascript`` on both sides.

The brython **special values** :data:`NULL` and :data:`UNDEFINED` are
real singletons with the brython semantics: falsy, ``NULL == UNDEFINED``
is ``True``, and the engine compares them by identity (``is``).
Everything else (``import_js``, ``console``, ``JSON``, ...) is a
:class:`~kopis.common.magic.Magic` dummy: non-essential on the server,
and it accepts any use so code does not complain.
"""

from ..common.magic import Magic

__all__ = [
    "JSON",
    "NULL",
    "UNDEFINED",
    "Array",
    "Date",
    "NullType",
    "RegExp",
    "String",
    "UndefinedType",
    "console",
    "extends",
    "import_js",
    "import_modules",
]


class _JSType:
    """Base of the brython Javascript special values."""

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        # In Javascript, null == undefined is true.
        return other is NULL or other is UNDEFINED

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return 0


class NullType(_JSType):
    """The brython ``javascript.NULL`` value (Javascript ``null``)."""

    def __str__(self) -> str:
        return "<Javascript null>"

    def __repr__(self) -> str:
        return "<Javascript null>"


class UndefinedType(_JSType):
    """The brython ``javascript.UNDEFINED`` value (Javascript
    ``undefined``)."""

    def __str__(self) -> str:
        # As in brython, the undefined value has no ``str`` conversion.
        raise TypeError(
            "descriptor '__str__' of 'object' object needs an argument"
        )

    def __repr__(self) -> str:
        return "<Javascript undefined>"


#: The brython special value for Javascript ``null``.
NULL = NullType()
#: The brython special value for Javascript ``undefined``.
UNDEFINED = UndefinedType()

# -- non-essential parts: Magic dummies -----------------------------------

import_js = Magic()
import_modules = Magic()
console = Magic()
JSON = Magic()
Array = Magic()
Date = Magic()
String = Magic()
RegExp = Magic()
extends = Magic()
this = Magic()


def __getattr__(name: str) -> Magic:
    # Any other (non-essential) name is a dummy stand-in.
    if name.startswith("_"):
        raise AttributeError(name)
    return Magic()
