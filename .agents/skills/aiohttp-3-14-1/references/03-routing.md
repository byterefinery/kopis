# Routing

## Table of Contents

- [Direct routing](#direct-routing)
- [RouteTableDef (decorators)](#routetabledef)
- [Route patterns](#route-patterns)
- [View classes](#view-classes)
- [Static files](#static-files)
- [UrlDispatcher](#urldispatcher)
- [URL generation](#url-generation)
- [Sub-applications](#sub-applications)
- [Domain matching](#domain-matching)

---

## Direct routing

```python
app = web.Application()

# Add by method
app.router.add_get("/", index_handler)
app.router.add_post("/items", create_item)
app.router.add_put("/items/{item_id}", update_item)
app.router.add_patch("/items/{item_id}", patch_item)
app.router.add_delete("/items/{item_id}", delete_item)
app.router.add_route("GET", "/custom", handler)  # arbitrary method
```

---

## RouteTableDef

Decorator-based routing with `RouteTableDef`:

```python
routes = web.RouteTableDef()

@routes.get("/")
async def index(request: web.Request) -> web.Response:
    return web.Response(text="Home")

@routes.get("/items/{item_id}")
async def get_item(request: web.Request) -> web.Response:
    return web.json_response({"id": request.match_info["item_id"]})

@routes.post("/items")
async def create_item(request: web.Request) -> web.Response:
    data = await request.json()
    return web.json_response(data, status=201)

@routes.put("/items/{item_id}")
async def update_item(request: web.Request) -> web.Response:
    ...

@routes.delete("/items/{item_id}")
async def delete_item(request: web.Request) -> web.Response:
    ...

@routes.options("/items")
async def options_handler(request: web.Request) -> web.Response:
    return web.Response()

@routes.view("/resource")
class ResourceView(web.View):
    async def get(self) -> web.Response:
        return web.Response(text="GET")
    async def post(self) -> web.Response:
        return web.Response(text="POST")

app = web.Application()
app.router.add_routes(routes)
```

### RouteTableDef as decorator factory

```python
routes = web.RouteTableDef()

@routes.get("/items", name="items_list")
async def list_items(request): ...

@routes.route("GET", "/items/{id}", name="item_detail")
async def get_item(request): ...
```

---

## Route patterns

### Static paths

```python
app.router.add_get("/api/health", health_check)
app.router.add_get("/", index)
```

### Dynamic paths

```python
# Simple parameter
app.router.add_get("/items/{item_id}", get_item)

# Multiple parameters
app.router.add_get("/users/{user_id}/posts/{post_id}", get_post)

# With regex constraint
app.router.add_get("/items/{item_id:\\d+}", get_item)
app.router.add_get("/files/{path:.+}", get_file)  # catch-all path segment
```

Parameter names must match `[_a-zA-Z][_a-zA-Z0-9]*`.

### Accessing parameters

```python
async def handler(request: web.Request):
    item_id = request.match_info["item_id"]  # always str
    # For numeric: int(request.match_info["item_id"])
```

---

## View classes

`web.View` enables class-based handlers with method dispatch:

```python
class ItemView(web.View):
    async def get(self) -> web.StreamResponse:
        return web.json_response({"id": self.request.match_info["id"]})

    async def post(self) -> web.StreamResponse:
        data = await self.request.json()
        return web.json_response(data, status=201)

    async def delete(self) -> web.StreamResponse:
        return web.Response(status=204)

app.router.add_view("/items/{id}", ItemView)
```

### View properties

| Property | Type | Description |
|---|---|---|
| `view.request` | `Request` | Current request |
| `view.app` | `Application` | Current application |
| `view.handler` | `Handler` | Matched handler |

### catch_all method

```python
class ItemView(web.View):
    async def catch_all(self) -> web.StreamResponse:
        return web.Response(status=405)  # Method Not Allowed
```

---

## Static files

Serve a directory of static files:

```python
# Basic
app.router.add_static("/static/", "/path/to/static/files/")

# With configuration
app.router.add_static(
    "/static/",
    "/path/to/static/",
    name="static",
    follow_symlinks=False,      # Follow symlinks (security risk)
    chunk_size=256*1024,        # Chunk size for sendfile
    show_index_stub=False,      # Directory listing
)
```

### With RouteTableDef

```python
@routes.static("/assets", "/path/to/assets")
async def static_handler(request): ...  # Not used; decorator registers route
```

Or:

```python
routes.static("/assets", "/path/to/assets")
```

---

## UrlDispatcher

The router object. Access via `app.router`.

### Methods

```python
# Add routes
app.router.add_get("/path", handler, name="named_route")
app.router.add_post("/path", handler)
app.router.add_route("PATCH", "/path", handler)
app.router.add_routes(routes_table)
app.router.add_static("/static/", "/path/")

# URL generation
url = app.router.url_for("named_route", param="value")

# Resolve request
match_info = await app.router.resolve(request)
```

### Resources and routes

```python
for resource in app.router.resources():
    print(resource.canonical)  # /path/{param}
    for route in resource:
        print(route.method, route.handler)
```

---

## URL generation

Generate URLs from named routes:

```python
# In handler
url = request.app.router.url_for("item_detail", item_id="123")
# Returns URL: /items/123

# With query params
url = request.app.router.url_for("search", q="hello").with_query(page="1")
```

### Route naming

```python
app.router.add_get("/items/{item_id}", get_item, name="item_detail")
# or
@routes.get("/items/{item_id}", name="item_detail")
async def get_item(request): ...
```

---

## Sub-applications

```python
# Create sub-app
api_app = web.Application()
api_app.router.add_get("/users", list_users)
api_app.router.add_get("/items", list_items)

# Mount
main_app = web.Application()
main_app.add_subapp("/api", api_app)

# Routes are now at /api/users, /api/items
```

### Sub-app middlewares

```python
api_app = web.Application(middlewares=[api_auth_middleware])
main_app.add_subapp("/api", api_app)
# api_auth_middleware runs for all /api/* routes
```

### Accessing sub-app from handler

```python
async def handler(request: web.Request):
    # Current app (could be sub-app)
    current = request.match_info.current_app
    # All apps in chain
    all_apps = request.match_info.apps
```

---

## Domain matching

Restrict routes to specific domains:

```python
from aiohttp.web_urldispatcher import Domain, MaskDomain

# Exact domain match
app.router.add_get("/", handler, domain=Domain("example.com"))

# Multiple domains
app.router.add_get("/", handler, domain=MaskDomain("example.com", "www.example.com"))
```
