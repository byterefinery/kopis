import platform


if platform.python_implementation() != 'Brython':
    # Server
    from unittest.mock import MagicMock

    javascript = MagicMock()
else:
    # Client
    import javascript  # noqa: F401 # ty: ignore[unresolved-import]
