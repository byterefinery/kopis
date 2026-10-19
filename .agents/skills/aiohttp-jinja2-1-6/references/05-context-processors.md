# Context Processors

## Overview

Context processors are async callables that inject shared variables into every template render. They run as middleware before the request handler, building a base context that the handler's context merges on top of.

## Signature

```python
_ContextProcessor = Callable[[web.Request], Awaitable[Dict[str, Any]]]
```

Each processor receives the `web.Request` and returns a dict of variables to merge into the template context.

## Built-in Processor

### request_processor

```python
async def request_processor(request: web.Request) -> Dict[str, web.Request]:
    return {"request": request}
```

Exposes the `request` object in templates:

```jinja2
{# Access request properties #}
Current path: {{ request.path }}
Query string: {{ request.query_string }}
Method: {{ request.method }}
Host: {{ request.host }}
Scheme: {{ request.scheme }}
```

## Registration

### Via setup()

```python
async def auth_processor(request: web.Request) -> dict:
    return {
        'is_authenticated': 'user' in request,
        'user': request.get('user'),
    }

aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates'),
    context_processors=(
        aiohttp_jinja2.request_processor,
        auth_processor,
    ),
)
```

This automatically registers the context processors middleware.

### Via AppKey (manual)

```python
app[aiohttp_jinja2.APP_CONTEXT_PROCESSORS_KEY] = (
    aiohttp_jinja2.request_processor,
    auth_processor,
)
app.middlewares.append(aiohttp_jinja2.context_processors_middleware)
```

## Middleware

The `context_processors_middleware` is an aiohttp middleware that:

1. Checks if `REQUEST_CONTEXT_KEY` exists on the request
2. If not, initializes it as an empty dict
3. Runs each processor in order, merging results into the request context
4. Passes the request to the handler

```python
@web.middleware
async def context_processors_middleware(
    request: web.Request,
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
) -> web.StreamResponse:
    if REQUEST_CONTEXT_KEY not in request:
        request[REQUEST_CONTEXT_KEY] = {}
    for processor in request.config_dict[APP_CONTEXT_PROCESSORS_KEY]:
        request[REQUEST_CONTEXT_KEY].update(await processor(request))
    return await handler(request)
```

## Context Merging Rules

1. Processors run in registration order
2. Later processors overwrite earlier values for the same key
3. Handler context takes final precedence (overwrites all processor values)
4. The handler's original dict is never mutated

```python
# Processor A returns: {'foo': 1, 'bar': 'a'}
# Processor B returns: {'bar': 'b', 'baz': 3}
# Handler returns:    {'bar': 'c'}
# Final context:      {'foo': 1, 'bar': 'c', 'baz': 3}
```

## Sub-Application Inheritance

Context processors compose across parent/child applications:

```python
# Parent app
parent = web.Application()
aiohttp_jinja2.setup(
    parent,
    loader=jinja2.FileSystemLoader('templates'),
    context_processors=(aiohttp_jinja2.request_processor, parent_processor),
)

# Sub-app
subapp = web.Application()
aiohttp_jinja2.setup(
    subapp,
    loader=jinja2.FileSystemLoader('templates/sub'),
    context_processors=(aiohttp_jinja2.request_processor, sub_processor),
)

parent.add_subapp('/sub/', subapp)
```

The sub-app's processors run in addition to the parent's. The middleware is registered on each app independently.

## Common Patterns

### Authentication context

```python
async def auth_context(request: web.Request) -> dict:
    session = await get_session(request)
    user_id = session.get('user_id')
    if user_id:
        user = await db.get_user(user_id)
        return {'user': user, 'is_authenticated': True}
    return {'user': None, 'is_authenticated': False}
```

### Site configuration

```python
async def site_config(request: web.Request) -> dict:
    config = request.app['config']
    return {
        'site_name': config['site_name'],
        'site_url': config['site_url'],
        'maintenance_mode': config.get('maintenance', False),
    }
```

### Flash messages

```python
async def flash_context(request: web.Request) -> dict:
    session = await get_session(request)
    return {'flash_messages': session.pop('flash', [])}
```

### I18n / locale

```python
async def locale_context(request: web.Request) -> dict:
    lang = request.headers.get('Accept-Language', 'en').split(',')[0]
    return {
        'lang': lang,
        'gettext': lambda s: translations.get(lang, {}).get(s, s),
    }
```

## Keys

- `APP_CONTEXT_PROCESSORS_KEY` — `web.AppKey[Sequence[ContextProcessor]]` storing the processor list on the app
- `REQUEST_CONTEXT_KEY` — string `'aiohttp_jinja2_context'` storing the merged context on the request
