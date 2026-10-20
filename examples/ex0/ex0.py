from pathlib import Path

import brython
import kopis
from kopis import Kopis


# Locate the JavaScript files shipped with the installed `brython` package.
brython_path = Path(brython.__file__).parent
brython_js_path = brython_path / "data" / "brython.js"
brython_stdlib_js_path = brython_path / "data" / "brython_stdlib.js"

# Locate the Python modules shipped with the installed `kopis` package.
kopis_path = Path(kopis.__file__).parent
browser_py_path = kopis_path / "brython" / "browser.py"

k = Kopis()

# Serve the brython scripts from where the package installed them.
k.add_static_file("/brython.js", brython_js_path)
k.add_static_file("/brython_stdlib.js", brython_stdlib_js_path)

# Serve the kopis package at the URLs Brython's import system expects,
# so e.g. ``from kopis.brython.browser import ...`` in client.py resolves.
k.add_static_file("/kopis/__init__.py", kopis_path / "__init__.py")
k.add_static_file("/kopis/brython/__init__.py", kopis_path / "brython" / "__init__.py")
k.add_static_file("/kopis/brython/browser.py", browser_py_path)

k.document = """
<html>
    <head>
        <meta charset="utf-8">
    </head>

    <body>
    </body>
</html>
"""

with k.document["head"] as el:
    el.add('<meta name="viewport" content="width=device-width, initial-scale=1">')
    el.add(f'<script type="text/javascript" src="{brython_js_path.name}"></script>')
    el.add(f'<script type="text/javascript" src="{brython_stdlib_js_path.name}"></script>')

with k.document.body as el:
    el.add("""
        <button id="btn0">
            Demo
        </button>

        <script type="text/python" src="/client.py"></script>
    """)

k.run()
