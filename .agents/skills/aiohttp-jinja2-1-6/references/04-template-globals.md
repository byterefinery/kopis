# Template Globals

## Built-in Globals

When `default_helpers=True` (the default), `setup()` registers these globals:

### `url(route_name, **parts, query_=None)`

Generates a URL from an aiohttp route name. Accepts path parameters as keyword arguments and an optional query string.

```jinja2
{# Simple route #}
<a href="{{ url('home') }}">Home</a>

{# Route with string param #}
<a href="{{ url('user_profile', name='alice') }}">Alice</a>

{# Route with int param #}
<a href="{{ url('article', id=42) }}">Article 42</a>

{# With query string #}
<a href="{{ url('search', query_={'q': 'python', 'page': '2'}) }}">Search</a>

{# Both params and query #}
<a href="{{ url('article_edit', id=5, query_={'draft': '1'}) }}">Edit</a>
```

The returned value is a `yarl.URL` object, which renders as a string in templates.

**Type restrictions:** Path parameters must be `str` or `int`. Passing `bool`, `float`, `list`, or other types raises `TypeError`. Note that `bool` is rejected even though it inherits from `int` — cast explicitly: `url('route', active=int(True))`.

### `static(path)`

Generates a URL for a static file by prepending the configured static root.

```jinja2
<link rel="stylesheet" href="{{ static('css/style.css') }}">
<script src="{{ static('js/app.js') }}"></script>
<img src="{{ static('images/logo.png') }}">
```

Requires setting the static root:

```python
app[aiohttp_jinja2.static_root_key] = '/static'
# Results in: /static/css/style.css

# CDN URL
app[aiohttp_jinja2.static_root_key] = 'https://cdn.example.com'
# Results in: https://cdn.example.com/css/style.css
```

Raises `RuntimeError` if `static_root_key` is not set.

### `app`

The `aiohttp.web.Application` instance is always available as a template global, regardless of `default_helpers`:

```jinja2
{# Access app settings #}
{{ app['site_name'] }}

{# Access registered routes #}
{{ app.router['home'].url_for() }}
```

## Custom Globals

Add custom globals through the Jinja2 environment:

```python
env = aiohttp_jinja2.get_env(app)

# Simple values
env.globals['year'] = 2024
env.globals['version'] = '1.0.0'

# Functions
env.globals['format_date'] = lambda dt: dt.strftime('%Y-%m-%d')
env.globals['current_time'] = lambda: datetime.now().isoformat()

# Objects
env.globals['config'] = app['config']
```

## Disabling Default Helpers

```python
aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates'),
    default_helpers=False,
)
```

This skips registering `url` and `static`. The `app` global is still available.

## GLOBAL_HELPERS Dictionary

The built-in helpers are stored in `aiohttp_jinja2.helpers.GLOBAL_HELPERS`:

```python
from aiohttp_jinja2.helpers import GLOBAL_HELPERS

# {'url': <url_for>, 'static': <static_url>}
```

These are `@jinja2.pass_context` decorated functions that access the template context to find the `app` object.

## url_for Implementation Details

The `url` global is a context function (`@jinja2.pass_context`) that:

1. Retrieves `app` from the template context
2. Looks up the route by name in `app.router`
3. Converts all path params to strings (int → str, str → str)
4. Calls `route.url_for(**parts)` to generate the URL
5. Optionally applies `query_` dict via `url.with_query()`

Route names must match those registered via `app.router.add_get('/', handler, name='home')` or similar.
