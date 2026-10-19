# setup() Configuration

## Signature

```python
def setup(
    app: web.Application,
    *args: Any,
    app_key: web.AppKey[jinja2.Environment] = APP_KEY,
    context_processors: Sequence[ContextProcessor] = (),
    filters: Optional[Filters] = None,
    default_helpers: bool = True,
    **kwargs: Any,
) -> jinja2.Environment:
```

## Parameters

### aiohttp-specific

| Parameter | Type | Default | Description |
|---|---|---|---|
| `app` | `web.Application` | — | The aiohttp application to attach the environment to |
| `app_key` | `web.AppKey[jinja2.Environment]` | `APP_KEY` | Key under which the environment is stored in the app dict |
| `context_processors` | `Sequence[ContextProcessor]` | `()` | Async callables that inject shared template variables |
| `filters` | `Mapping[str, Filter]` or `Iterable[Tuple[str, Filter]]` | `None` | Custom Jinja2 filters to register |
| `default_helpers` | `bool` | `True` | Whether to add `url` and `static` globals to templates |

### Jinja2 Environment parameters (via `*args`/`**kwargs`)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `loader` | `jinja2.BaseLoader` | — | Template loader (required in practice) |
| `autoescape` | `bool` | `True` (forced) | Auto-escape HTML in template output |
| `enable_async` | `bool` | `False` | Enable async template rendering (Jinja2 3.0+) |
| `block_start_string` | `str` | `{%` | Block open delimiter |
| `block_end_string` | `str` | `%}` | Block close delimiter |
| `variable_start_string` | `str` | `{{` | Variable open delimiter |
| `variable_end_string` | `str` | `}}` | Variable close delimiter |
| `comment_start_string` | `str` | `{#` | Comment open delimiter |
| `comment_end_string` | `str` | `#}` | Comment close delimiter |
| `trim_blocks` | `bool` | `False` | Remove first newline after block |
| `lstrip_blocks` | `bool` | `False` | Strip leading whitespace before blocks |
| `undefined` | `type` | `jinja2.Undefined` | Class for undefined variable behavior |
| `extensions` | `list[str]` | `[]` | Jinja2 extensions to load |

`autoescape` defaults to `True` unless explicitly set to `False`.

## Common Loaders

```python
import jinja2

# File system — most common for production
loader = jinja2.FileSystemLoader('/path/to/templates')

# Multiple directories (first match wins)
loader = jinja2.FileSystemLoader(['/app/templates', '/app/overrides'])

# In-memory — useful for testing
loader = jinja2.DictLoader({
    'index.html': '<h1>{{ title }}</h1>',
    'base.html': '<html>{% block body %}{% endblock %}</html>',
})

# From a Python package
loader = jinja2.PackageLoader('myapp', 'templates')

# Choice loader — tries loaders in order
loader = jinja2.ChoiceLoader([
    jinja2.PackageLoader('myapp', 'templates'),
    jinja2.FileSystemLoader('/local/overrides'),
])
```

## Multiple Environments

Use `app_key` to maintain separate Jinja2 environments on the same application:

```python
import jinja2
import aiohttp_jinja2
from aiohttp import web

admin_key = web.AppKey[jinja2.Environment]('admin_env')
public_key = web.AppKey[jinja2.Environment]('public_env')

aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates/admin'),
    app_key=admin_key,
)

aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates/public'),
    app_key=public_key,
)

# Use matching app_key in decorator or render function
@aiohttp_jinja2.template('admin.html', app_key=admin_key)
async def admin_panel(request):
    return {'user': 'admin'}

async def public_page(request):
    return aiohttp_jinja2.render_template(
        'index.html', request, {}, app_key=public_key
    )
```

Each environment has its own globals, filters, loader, and configuration.

## Enabling Async Templates

For Jinja2 3.0+ async template support:

```python
aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates'),
    enable_async=True,
)
```

With `enable_async=True`:
- `@template` decorator auto-switches to `render_template_async`
- `render_template()` still uses synchronous rendering
- Use `render_template_async()` explicitly for async rendering
- Templates can use `async for`, `async if`, and `async do` blocks

```jinja2
{# Async template example #}
{% for item in items async %}
    <li>{{ item.name }}</li>
{% endfor %}
```

## Disabling Default Helpers

```python
aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates'),
    default_helpers=False,
)
```

This removes `url` and `static` from template globals. Useful when you want to provide your own implementations or avoid the dependency on aiohttp routing.

## Post-setup Environment Access

```python
env = aiohttp_jinja2.get_env(app)

# Add globals
env.globals['year'] = 2024
env.globals['version'] = '1.0'

# Add filters
env.filters['slugify'] = slugify_func

# Configure loader at runtime
env.loader = jinja2.FileSystemLoader('new_templates')
```

## AppKey Details

The default `APP_KEY` is a `web.AppKey[jinja2.Environment]` with internal name `'APP_KEY'`. The `static_root_key` is a separate `web.AppKey[str]` with internal name `'static_root_key'`.

These `AppKey` objects provide type-safe dictionary access and avoid key collisions. They are preferred over plain string keys.
