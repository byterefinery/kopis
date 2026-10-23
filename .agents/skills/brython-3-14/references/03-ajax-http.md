# HTTP requests with browser.ajax

`browser.ajax` is the HTTP client of choice in Brython — `requests` and `urllib.request` cannot send arbitrary requests from a browser. Needs `brython_stdlib.js`.

## Concise interface

One function per method. GET-family: `get`, `connect`, `delete`, `head`, `options`, `trace`:

```
get(url, blocking=False, headers={}, mode="text", encoding="utf-8",
    timeout=None, cache=False, data="", **callbacks)
```

Body methods: `post`, `patch`, `put` — `data` carries the body (a dict is encoded as `x=1&y=2` and `Content-Length` is computed automatically; default `Content-Type` is `application/x-www-form-urlencoded`).

- `mode` — `"text"` (default), `"binary"`, `"json"` or `"document"`
- `blocking=False` — default is asynchronous; `True` blocks the script until the response
- `cache=False` — by default a random parameter is added to the GET to bypass the cache
- `timeout` — seconds after which the request is cancelled (an `ontimeout` callback, which takes no argument)
- `**callbacks` — keys of the form `on` + event name; in practice only `oncomplete` is defined

Callback signature — one argument, the Ajax object:

```python
from browser import ajax, document

def read(req):
    if req.status == 200:
        document["result"].html = req.text

ajax.get("data.json", mode="json", oncomplete=read)   # use req.json in the callback
```

Ajax object attributes: `status` (HTTP code), `text` (`str` for text/xml mode, `bytes` for binary; `AttributeError` in json mode), `json` (parsed object in json mode), `xml` (tree in document mode), `read()`.

## Async requests (browser.aio)

`browser.aio` is compiled into `brython.js` (no stdlib bundle needed) and supports `async`/`await` as the replacement for CPython's `asyncio`, which cannot work in the browser:

```python
from browser.aio import ajax

async def main():
    req = await ajax("GET", "data.json", format="json")
    ...    # req carries the response; see browser.aio.md in the 3.14 docs for the full Request interface
```

## Standard XMLHttpRequest interface

```python
from browser import ajax

req = ajax.Ajax()
req.bind("complete", on_complete)
req.open("POST", url, True)    # method, url, async
req.set_header("content-type", "application/x-www-form-urlencoded")
req.send({"x": 0, "y": 1})     # dict, string, or form_data
```

Methods and attributes: `open(method, url, async)`, `bind(evt, fn)`, `set_header(name, value)`, `set_timeout(seconds, fn)` (fn takes no argument), `encoding`, `responseType`, `withCredentials`, `send(data)`. All XMLHTTPRequest properties are available on the object.

## File upload

```python
from browser import ajax, bind, document

@bind("#upload", "click")
def upload(event):
    for f in document["choosefiles"].files:
        ajax.file_upload("/cgi-bin/savefile.py", f, oncomplete=done)
```

`file_upload(url, file, method="POST", field_name="filetosave", headers=..., timeout=..., data=..., **callbacks)`; `file` is usually `document["input"].files[i]`. For full control build a FormData object: `fd = ajax.form_data()` (or `ajax.form_data(form_element)` to read a FORM), `fd.append(name, value[, filename])`, then `req.send(fd)`.
