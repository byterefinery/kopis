import platform


if platform.python_implementation() != 'Brython':
    # Server
    from unittest.mock import MagicMock

    document = MagicMock()
    aio = MagicMock()
else:
    # Client
    from browser import document, aio  # noqa: F401 # ty: ignore[unresolved-import]
