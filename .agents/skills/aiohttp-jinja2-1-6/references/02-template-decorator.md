# @template Decorator

## Signature

```python
def template(
    template_name: str,
    *,
    app_key: web.AppKey[jinja2.Environment] = APP_KEY,
    encoding: str = 'utf-8',
    status: int = 200,
) -> TemplateWrapper:
```

## How It Works

The `@template` decorator wraps an aiohttp handler. On each request:

1. The original handler is called
2. If the handler returns a `web.StreamResponse`, it is returned directly (no rendering)
3. Otherwise, the returned dict is used as template context
4. The named template is rendered and a `web.Response` is returned with the specified encoding and status

## Basic Usage

```python
@aiohttp_jinja2.template('index.html')
async def index(request: web.Request) -> dict:
    return {'title': 'Home Page', 'items': [1, 2, 3]}
```

The handler returns a dict; the decorator renders `index.html` with that context and returns `web.Response(text=rendered_html, content_type='text/html', charset='utf-8')`.

## With Class-Based Views

```python
class ArticleView(web.View):
    @aiohttp_jinja2.template('article.html')
    async def get(self) -> dict:
        article_id = int(self.request.match_info['id'])
        article = await get_article(article_id)
        return {'article': article}

    @aiohttp_jinja2.template('edit.html')
    async def post(self) -> dict:
        data = await self.request.post()
        return {'form': data, 'errors': {}}
```

## With Bound Methods

```python
class Handler:
    @aiohttp_jinja2.template('page.html')
    async def handle(self, request: web.Request) -> dict:
        return {'page': 'about'}

handler = Handler()
app.router.add_get('/page', handler.handle)
```

## Custom Status Code

```python
@aiohttp_jinja2.template('created.html', status=201)
async def create(request: web.Request) -> dict:
    item_id = await save_item(await request.json())
    return {'item_id': item_id}
```

## Custom Encoding

```python
@aiohttp_jinja2.template('page.html', encoding='latin-1')
async def legacy_page(request: web.Request) -> dict:
    return {'content': legacy_text}
```

## Skipping Rendering

Return a `web.StreamResponse` (or subclass) to bypass template rendering:

```python
@aiohttp_jinja2.template('page.html')
async def handler(request: web.Request) -> web.StreamResponse | dict:
    if request.query.get('format') == 'json':
        return web.json_response({'status': 'ok'})
    if request.query.get('format') == 'redirect':
        raise web.HTTPFound('/other')
    return {'title': 'Page'}
```

Any `web.StreamResponse` subclass works: `web.Response`, `web.json_response()`, `web.HTTPFound()`, `web.HTTPNotFound()`, etc.

## Empty Context

Returning `None` (via `pass` or explicit `return None`) renders the template with an empty context:

```python
@aiohttp_jinja2.template('health.html')
async def health_check(request: web.Request) -> None:
    pass  # Renders with empty context
```

## Error Handling

| Error | Cause |
|---|---|
| `HTTPInternalServerError("Template engine is not initialized...")` | `setup()` not called before handler |
| `HTTPInternalServerError("Template 'name' not found")` | Template file not found by loader |
| `HTTPInternalServerError("context should be mapping, not <class 'int'>")` | Handler returned non-mapping, non-response value |
| `jinja2.TemplateError` | Syntax error or runtime error in template |

## Decorator Behavior with Async

When `enable_async=True` is set in `setup()`, the `@template` decorator automatically uses `render_template_async` for rendering. This means templates using `async for` or `async if` are supported without changing handler code.

## Type Signatures

The decorator preserves type information with overloads:

```python
# Simple handler
@aiohttp_jinja2.template('page.html')
async def handler(request: web.Request) -> dict:
    ...

# Class-based view
class View(web.View):
    @aiohttp_jinja2.template('page.html')
    async def get(self) -> dict:
        ...

# Bound method
class Handler:
    @aiohttp_jinja2.template('page.html')
    async def handle(self, request: web.Request) -> dict:
        ...
```

The decorated function's return type is `Callable[..., Awaitable[web.StreamResponse]]`.
