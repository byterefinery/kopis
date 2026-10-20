import platform
from typing import TYPE_CHECKING


if TYPE_CHECKING or platform.python_implementation() != 'Brython':
    # Server
    from unittest.mock import MagicMock

    document = MagicMock()
else:
    # Client
    from browser import document  # noqa: F401 # ty: ignore[unresolved-import]
