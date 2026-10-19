---
name: aiohttp-jinja2-1-6
description: >
  aiohttp-jinja2 1.6 — Jinja2 template rendering integration for aiohttp.web. Use this skill whenever
  the user works with Jinja2 templates in aiohttp web applications, needs server-side HTML rendering,
  template decorators on handlers, context processors for shared template variables, or URL generation
  inside Jinja2 templates. Provides setup(), @template decorator, render_template/render_string functions,
  built-in url() and static() template globals, and context processor middleware. Built on top of
  jinja2 and aiohttp.web.
metadata:
  tags:
    - python
    - web
    - aiohttp
    - templating
    - jinja2
---

# aiohttp-jinja2 1.6

`aiohttp_jinja2` bridges Jinja2 template rendering with `aiohttp.web`, providing a decorator-based approach for template handlers, direct render functions, and context processors for shared template variables.

## Overview

### Architecture

The library registers a Jinja2 `Environment` on an `aiohttp.web.Application` via `setup()`. Templates are looked up through a Jinja2 `Loader` (FileSystemLoader, DictLoader, PackageLoader, etc.). The environment is stored under an `AppKey` and accessed from request handlers or template globals.

### Key API

| Function | Purpose |
|---|---|
| `setup(app, loader=..., ...)` | Initialize Jinja2 environment on an aiohttp app |
| `@template('name.jinja2')` | Decorate handlers to auto-render templates |
| `render_template(name, request, context)` | Render template, return `web.Response` |
| `render_template_async(...)` | Async version of render_template |
| `render_string(name, request, context)` | Render template to plain string |
| `render_string_async(...)` | Async version of render_string |
| `get_env(app)` | Retrieve the Jinja2 Environment from an app |

### Built-in Template Globals

When `default_helpers=True` (the default), two helper functions are available in all templates:

- **`url(route_name, **parts, query_=None)`** — Generate URLs from aiohttp route names. Accepts `str` or `int` path params and an optional `query_` dict.
- **`static(path)`** — Generate static file URLs. Requires `app[aiohttp_jinja2.static_root_key]` to be set.

The `app` object (the `web.Application`) is also always available as a template global.

### Context Processors

Context processors are async callables `(request) -> Dict[str, Any]` that inject shared variables into every template render. They run via middleware before the handler. The built-in `request_processor` exposes the `request` object in templates.

## Usage

### Basic setup and rendering

```python
import jinja2
import aiohttp_jinja2
from aiohttp import web

app = web.Application()

# Initialize — FileSystemLoader is most common for production
aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('/path/to/templates'),
)

# Decorator style — handler returns context dict, template auto-renders
@aiohttp_jinja2.template('index.html')
async def index(request: web.Request) -> dict:
    return {'title': 'Home', 'items': [1, 2, 3]}

# Direct rendering — full control over response
async def detail(request: web.Request) -> web.Response:
    context = {'item': {'name': 'Widget'}}
    response = aiohttp_jinja2.render_template('detail.html', request, context)
    response.headers['Content-Language'] = 'en'
    return response

app.router.add_get('/', index)
app.router.add_get('/detail', detail)
web.run_app(app)
```

### Class-based views

```python
class Dashboard(web.View):
    @aiohttp_jinja2.template('dashboard.html')
    async def get(self) -> dict:
        return {'user': 'Alice', 'stats': {'views': 42}}
```

### Custom status and encoding

```python
# Via decorator
@aiohttp_jinja2.template('created.html', status=201, encoding='utf-8')
async def create_item(request):
    return {'item_id': 123}

# Via render_template
response = aiohttp_jinja2.render_template(
    'error.html', request, {'code': 404}, status=404
)
```

### Async template rendering

Jinja2 3.0+ supports async templates (with `async for`, `async if`). Enable with `enable_async=True` in setup:

```python
aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates'),
    enable_async=True,
)

# Use render_template_async or render_string_async
async def handler(request):
    response = await aiohttp_jinja2.render_template_async(
        'async_template.html', request, {'data': items}
    )
    return response

# @template decorator auto-detects: uses async rendering when enable_async=True
```

### Context processors

```python
async def auth_processor(request: web.Request) -> dict:
    return {'is_authenticated': 'user' in request}

async def settings_processor(request: web.Request) -> dict:
    return {'site_name': request.app['site_name']}

aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates'),
    context_processors=(
        aiohttp_jinja2.request_processor,  # exposes {{ request }}
        auth_processor,
        settings_processor,
    ),
)
```

Context from processors is merged into every render. Handler-provided context takes precedence (overwrites same keys).

### Custom Jinja2 filters

```python
def currency(value: float) -> str:
    return f'${value:,.2f}'

def truncate_words(value: str, max_words: int = 10) -> str:
    words = value.split()
    return ' '.join(words[:max_words]) + ('...' if len(words) > max_words else '')

aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates'),
    filters={'currency': currency, 'truncate_words': truncate_words},
)
```

### URL generation in templates

```jinja2
{# Route with path params (str or int) #}
<a href="{{ url('user_profile', name='alice') }}">Alice</a>
<a href="{{ url('article', id=42)}}">Article 42</a>

{# With query string #}
<a href="{{ url('search', query_={'q': 'python', 'page': '1'}) }}">Search</a>

{# Static file URL #}
<link rel="stylesheet" href="{{ static('css/style.css') }}">
```

Set the static root:

```python
app[aiohttp_jinja2.static_root_key] = '/static'
# or a CDN URL
app[aiohttp_jinja2.static_root_key] = 'https://cdn.example.com'
```

### Accessing the Jinja2 environment

```python
env = aiohttp_jinja2.get_env(app)

# Add globals or filters after setup
env.globals['current_year'] = 2024
env.filters['upper'] = str.upper
```

### Skipping template rendering

Return a `web.StreamResponse` (or subclass) from a decorated handler to bypass rendering:

```python
@aiohttp_jinja2.template('page.html')
async def handler(request):
    if request.query.get('json'):
        return web.json_response({'status': 'ok'})
    return {'title': 'Page'}
```

### Multiple template environments

Use `app_key` to maintain separate environments:

```python
admin_key = web.AppKey[jinja2.Environment]('admin_env')
aiohttp_jinja2.setup(app, loader=..., app_key=admin_key)

@aiohttp_jinja2.template('admin.html', app_key=admin_key)
async def admin_handler(request):
    return {}
```

## Gotchas

- **`setup()` must be called before any rendering** — Calling `render_template()` or using `@template` before `setup()` raises `HTTPInternalServerError`. Initialize during app construction, not in a handler.
- **Handler must return a `Mapping` (dict)** — The `@template` decorator expects the handler to return a dict-like context. Returning `None` works (empty context), but returning a non-mapping (int, list, str) raises `HTTPInternalServerError`.
- **`autoescape=True` by default** — `setup()` sets `autoescape=True` automatically. HTML in context values is escaped unless wrapped in `jinja2.Markup()`. Disable with `autoescape=False` if rendering trusted HTML.
- **`url()` only accepts `str` or `int` params** — Passing `bool`, `float`, or other types to `url()` raises `TypeError`. Booleans are rejected even though `bool` inherits from `int` — cast explicitly: `url('route', flag=int(True))`.
- **`static()` requires `static_root_key`** — Using `{{ static('file.css') }}` without setting `app[aiohttp_jinja2.static_root_key]` raises `RuntimeError`. The old `app['static_root_url']` key is deprecated.
- **Context processors run in order, later values win** — If two processors set the same key, the later processor's value is used. Handler context still takes final precedence.
- **Context is not mutated** — The handler's context dict is not modified by context processors. A new merged dict is created internally, so shared global dicts stay clean.
- **`enable_async` changes behavior of `@template`** — When `enable_async=True` is passed to `setup()`, the `@template` decorator automatically uses `render_template_async` instead of `render_template`. No handler change needed.
- **Sub-apps inherit parent environment** — Templates use `request.config_dict` which walks up the app hierarchy. A sub-app without its own `setup()` inherits the parent's Jinja2 environment.
- **`default_helpers=False` removes `url` and `static`** — Disabling default helpers means templates lose `{{ url(...) }}` and `{{ static(...) }}`. Re-add them manually via `env.globals` if needed.
- **`@template` on bound methods works** — Decorating a method on a plain class (not `web.View`) works when registered as `app.router.add_route('*', '/', handler_instance.method)`. The decorator detects `web.View` instances and plain bound methods.
- **`context_processors` in `setup()` auto-registers middleware** — Passing `context_processors=` to `setup()` appends the context processors middleware automatically. No need to manually add it to `app.middlewares`.
- **`get_env()` raises `RuntimeError` if not set up** — Accessing the environment without prior `setup()` raises `RuntimeError`. Use `app.get(app_key)` for safe optional access.

## References

- [01-setup-configuration](references/01-setup-configuration.md) — setup() parameters, Jinja2 Environment options, multi-env
- [02-template-decorator](references/02-template-decorator.md) — @template decorator, handler patterns, response bypass
- [03-render-functions](references/03-render-functions.md) — render_template, render_string, async variants, error handling
- [04-template-globals](references/04-template-globals.md) — url(), static(), app global, custom globals
- [05-context-processors](references/05-context-processors.md) — Context processor middleware, request_processor, sub-app inheritance
- [06-filters-and-helpers](references/06-filters-and-helpers.md) — Custom filters, default helpers, GLOBAL_HELPERS
