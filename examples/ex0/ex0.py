from pathlib import Path

import brython
from kopis import Kopis

# Locate the JavaScript files shipped with the installed `brython` package.
brython_path = Path(brython.__file__).parent
brython_js_path = brython_path / "data" / "brython.js"
brython_stdlib_js_path = brython_path / "data" / "brython_stdlib.js"

k = Kopis()

# Serve the brython scripts from where the package installed them.
k.add_static_file("/brython.js", brython_js_path)
k.add_static_file("/brython_stdlib.js", brython_stdlib_js_path)

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
    el.add(
        f'<script type="text/javascript" src="{brython_stdlib_js_path.name}"></script>'
    )

with k.document.body as el:
    el.add("""
        <button id="btn0">
            Demo
        </button>

        <script type="text/python">
            from browser import document
            document <= "Hello 3 !"

            def btn0_click(e):
                print('btn0_click', e)

            document.querySelector('#btn0') \
                .bind('click', btn0_click)
        </script>
    """)

k.run()
