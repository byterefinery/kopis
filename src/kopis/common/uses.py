"""Client-side dependencies for :meth:`KopisBase.use`.

``USES`` maps the short name of a client-side dependency to the HTML
fragment it needs in the document head — its ``<script>`` and
``<link>`` elements, pinned to a working URL. ``"brython"`` is the
default dependency, like any other: its scripts (the Brython engine
and the standard library bundle) are served by the server at
``/brython.js`` and ``/brython_stdlib.js`` and annotated into the
served document's head, so the application code runs in the browser
under Brython. A dependency may need several elements (``"oat"`` is a stylesheet and a
script; ``"daisyui"`` is two stylesheets plus the Tailwind browser
build that processes them), and elements may be shared between
dependencies (both ``"daisyui"`` and ``"tailwindcss"`` need the
Tailwind browser build); :meth:`KopisBase.use` skips an element whose
URL is already in the head, so each URL is loaded at most once.
"""

USES: dict[str, str] = {
    "brython": (
        '<script src="/brython.js"></script><script src="/brython_stdlib.js"></script>'
    ),
    "alpinejs": '<script src="//unpkg.com/alpinejs" defer></script>',
    "tailwindcss": (
        '<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>'
    ),
    "daisyui": (
        '<link href="https://cdn.jsdelivr.net/npm/daisyui@5" rel="stylesheet" type="text/css" />'
        '<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>'
        '<link href="https://cdn.jsdelivr.net/npm/daisyui@5/themes.css" rel="stylesheet" type="text/css" />'
    ),
    "lodash": (
        '<script src="https://cdn.jsdelivr.net/npm/lodash@4.18.1/lodash.min.js"></script>'
    ),
    "axios": (
        '<script src="https://cdn.jsdelivr.net/npm/axios@1.20.0/dist/axios.min.js"></script>'
    ),
    "oat": (
        '<link rel="stylesheet" href="https://unpkg.com/@knadh/oat/oat.min.css">'
        '<script src="https://unpkg.com/@knadh/oat/oat.min.js" defer></script>'
    ),
}
