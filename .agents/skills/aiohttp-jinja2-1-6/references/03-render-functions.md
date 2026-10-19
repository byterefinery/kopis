# Render Functions

## render_template

```python
def render_template(
    template_name: str,
    request: web.Request,
    context: Optional[Mapping[str, Any]],
    *,
    app_key: web.AppKey[jinja2.Environment] = APP_KEY,
    encoding: str = 'utf-8',
    status: int = 200,
) -> web.Response:
```

Renders a template and returns a `web.Response` with `content_type='text/html'` and the specified charset.

```python
async def handler(request: web.Request) -> web.Response:
    context = {'user': user, 'items': items}
    response = aiohttp_jinja2.render_template('dashboard.html', request, context)
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Frame-Options'] = 'DENY'
    return response
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `template_name` | `str` | — | Template name for the loader |
| `request` | `web.Request` | — | The current aiohttp request |
| `context` | `Mapping[str, Any]` or `None` | — | Template context (None = empty dict) |
| `app_key` | `web.AppKey` | `APP_KEY` | Key for the Jinja2 environment |
| `encoding` | `str` | `'utf-8'` | Response charset |
| `status` | `int` | `200` | HTTP status code |

## render_template_async

```python
async def render_template_async(
    template_name: str,
    request: web.Request,
    context: Optional[Mapping[str, Any]],
    *,
    app_key: web.AppKey[jinja2.Environment] = APP_KEY,
    encoding: str = 'utf-8',
    status: int = 200,
) -> web.Response:
```

Async version. Uses Jinja2's `template.render_async()` which supports `async for` and `async if` in templates. Requires `enable_async=True` in `setup()`.

```python
async def handler(request: web.Request) -> web.Response:
    return await aiohttp_jinja2.render_template_async(
        'async_page.html', request, {'items': async_items}
    )
```

## render_string

```python
def render_string(
    template_name: str,
    request: web.Request,
    context: Mapping[str, Any],
    *,
    app_key: web.AppKey[jinja2.Environment] = APP_KEY,
) -> str:
```

Renders a template and returns the resulting string. No HTTP response is created.

```python
async def handler(request: web.Request) -> web.Response:
    html = aiohttp_jinja2.render_string('email_body.html', request, {'user': user})
    # Send via email, save to file, etc.
    return web.Response(text=html)
```

## render_string_async

```python
async def render_string_async(
    template_name: str,
    request: web.Request,
    context: Mapping[str, Any],
    *,
    app_key: web.AppKey[jinja2.Environment] = APP_KEY,
) -> str:
```

Async version of `render_string`.

## Context Merging with Context Processors

When context processors are active, the handler's context is merged on top of the processor context:

```python
# Processor sets: {'site_name': 'MyApp', 'user': None}
# Handler returns: {'user': alice, 'items': [...]}
# Final context: {'site_name': 'MyApp', 'user': alice, 'items': [...]}
```

Handler values take precedence. The original handler dict is not mutated.

## Error Cases

All render functions raise `web.HTTPInternalServerError` in these cases:

1. **Engine not initialized** — `setup()` was not called. Message: `"Template engine is not initialized, call aiohttp_jinja2.setup() first"`

2. **Template not found** — Loader cannot find the template. Message: `"Template 'name' not found"`

3. **Invalid context** — Context is not a Mapping. Message: `"context should be mapping, not <class 'X'>"`

For `render_template` and `render_template_async`, `context=None` is accepted and treated as empty dict `{}`. For `render_string` and `render_string_async`, `context` must be a Mapping.

## Comparison

| Function | Returns | Async | Context can be None | Response control |
|---|---|---|---|---|
| `render_template` | `web.Response` | No | Yes | Full (headers, status) |
| `render_template_async` | `web.Response` | Yes | Yes | Full (headers, status) |
| `render_string` | `str` | No | No | None |
| `render_string_async` | `str` | Yes | No | None |

Use `render_template` when you need to set response headers or custom status. Use `render_string` when you need the rendered text for non-HTTP purposes (email, caching, file output).
