# Filters and Helpers

## Custom Filters

Register custom Jinja2 filters via the `filters` parameter in `setup()`:

```python
def currency(value: float) -> str:
    return f'${value:,.2f}'

def initial(value: str) -> str:
    return value[0].upper() if value else ''

aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates'),
    filters={
        'currency': currency,
        'initial': initial,
    },
)
```

Usage in templates:

```jinja2
{{ price|currency }}
{{ user.name|initial }}
```

### Filter as Iterable

Filters can also be passed as an iterable of `(name, func)` tuples:

```python
aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates'),
    filters=[
        ('currency', currency),
        ('initial', initial),
    ],
)
```

### Adding Filters After Setup

```python
env = aiohttp_jinja2.get_env(app)
env.filters['slugify'] = slugify_func
env.filters['markdown'] = markdown_to_html
```

## Built-in Jinja2 Filters

All standard Jinja2 filters are available:

| Filter | Description |
|---|---|
| `abs`, `round` | Numeric operations |
| `lower`, `upper`, `title`, `capitalize` | String case |
| `trim`, `strip`, `replace` | String manipulation |
| `length`, `count` | Collection size |
| `first`, `last`, `sort`, `reverse` | Sequences |
| `default` | Fallback value |
| `safe` | Mark as safe (skip autoescape) |
| `escape` | Explicitly escape |
| `e` | Alias for `escape` |
| `int`, `float` | Type conversion |
| `json_encode` | JSON serialization |
| `urlencode` | URL query encoding |
| `wordwrap`, `truncate` | Text formatting |
| `datetimeformat` | Date formatting (with extension) |

## default_helpers Parameter

```python
aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates'),
    default_helpers=False,  # No url() or static() in templates
)
```

When `False`, the `url` and `static` globals are not registered. The `app` global remains available.

## GLOBAL_HELPERS

The built-in helpers are defined in `aiohttp_jinja2.helpers`:

```python
from aiohttp_jinja2.helpers import GLOBAL_HELPERS, url_for, static_url

# GLOBAL_HELPERS = {'url': url_for, 'static': static_url}
```

Both `url_for` and `static_url` are decorated with `@jinja2.pass_context`, which gives them access to the template context (needed to find the `app` object).

## url_for (url) Implementation

```python
@jinja2.pass_context
def url_for(
    context: Dict[str, Any],
    __route_name: str,
    query_: Optional[Dict[str, str]] = None,
    **parts: Union[str, int],
) -> URL:
```

- `__route_name` — the aiohttp route name (e.g., `'user_profile'`)
- `**parts` — path parameters (must be `str` or `int`)
- `query_` — optional dict for query string parameters

Returns a `yarl.URL` object.

## static_url (static) Implementation

```python
@jinja2.pass_context
def static_url(context: Dict[str, Any], static_file_path: str) -> str:
```

- `static_file_path` — relative path to the static file

Returns a string URL by prepending the value of `app[static_root_key]`.

## static_root_key

```python
from aiohttp_jinja2 import static_root_key

app[static_root_key] = '/static'
```

This is a `web.AppKey[str]` (type-safe). The old plain-string key `app['static_root_url']` is deprecated and triggers a `DeprecationWarning`.

## Filters Type Definition

```python
from aiohttp_jinja2.typedefs import Filters

# Filters = Union[Iterable[Tuple[str, Filter]], Mapping[str, Filter]]
# Filter = Callable[..., str]
```
