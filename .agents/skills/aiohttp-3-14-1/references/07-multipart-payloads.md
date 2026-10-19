# Multipart and Payloads

## Table of Contents

- [FormData](#formdata)
- [MultipartReader](#multipartreader)
- [MultipartWriter](#multipartwriter)
- [BodyPartReader](#bodypartreader)
- [Payload system](#payload-system)
- [Payload types](#payload-types)
- [Payload registry](#payload-registry)
- [streamer()](#streamer)

---

## FormData

Helper for building form submissions (url-encoded or multipart):

```python
from aiohttp import FormData

# Simple url-encoded form
form = FormData()
form.add_field("username", "john")
form.add_field("password", "secret")

async with session.post(url, data=form) as resp:
    ...

# Multipart with file upload
form = FormData()
form.add_field("username", "john")
form.add_field(
    "avatar",
    open("photo.jpg", "rb"),
    filename="photo.jpg",
    content_type="image/jpeg",
)

async with session.post(url, data=form) as resp:
    ...
```

### add_field()

```python
form.add_field(
    name="file",
    value=data,                    # bytes, str, file-like
    content_type="application/pdf",
    filename="document.pdf",
)
```

### is_multipart

```python
form = FormData()
form.add_field("key", "value")
print(form.is_multipart)  # False — will be url-encoded

form.add_field("file", open("data.bin", "rb"))
print(form.is_multipart)  # True — will be multipart/form-data
```

### Constructor shortcuts

```python
# From dict
form = FormData({"key1": "val1", "key2": "val2"})

# From list of tuples
form = FormData([("key1", "val1"), ("key2", "val2")])

# Force multipart
form = FormData(default_to_multipart=True)
```

---

## MultipartReader

Read incoming multipart data (server-side or client-side):

```python
# Server — from request
async def handler(request: web.Request):
    if not request.content_type.startswith("multipart/"):
        return web.HTTPBadRequest()

    reader = await request.multipart()
    async for part in reader:
        print(part.name)           # Field name
        print(part.filename)       # Filename (None for non-file fields)
        print(part.content_type)   # Content-Type

        if part.filename:
            data = await part.read()
        else:
            text = await part.text()
```

```python
# Client — from response
async with session.post(url, data=form) as resp:
    if resp.content_type.startswith("multipart/"):
        reader = aiohttp.MultipartReader(resp)
        async for part in reader:
            data = await part.read()
```

### Nested multipart

```python
async for part in reader:
    if part.is_multipart:
        nested_reader = await part.multipart()
        async for nested_part in nested_reader:
            ...
```

---

## MultipartWriter

Build multipart responses:

```python
writer = aiohttp.MultipartWriter("mixed")

writer.append("text part")
writer.append_payload(aiohttp.BytesPayload(b"binary"))
writer.append(json={"key": "value"}, content_type="application/json")

return web.Response(body=writer, content_type=writer.content_type)
```

### Subtypes

```python
MultipartWriter("form-data")   # multipart/form-data
MultipartWriter("mixed")       # multipart/mixed
MultipartWriter("alternative") # multipart/alternative
MultipartWriter("related")     # multipart/related
MultipartWriter("digest")      # multipart/digest
```

---

## BodyPartReader

Individual part from a multipart message:

```python
async for part in reader:
    # Properties
    part.name             # str — field name
    part.filename         # str | None
    part.content_type     # str
    part.headers          # CIMultiDictProxy — part headers
    part.is_multipart     # bool

    # Reading
    data: bytes = await part.read()       # Full body as bytes
    text: str = await part.text()         # Full body as text
    json_data = await part.json()         # Parsed JSON

    # Streaming
    async for chunk in part.iter_chunked(4096):
        process(chunk)

    # Skip
    await part.skip()
```

---

## Payload system

Payloads wrap request/response body data with content-type detection:

```python
from aiohttp import payload

# Auto-detect payload type
p = payload.get_payload(b"hello")
print(p.content_type)  # "application/octet-stream"

# Explicit content type
p = payload.get_payload(b"hello", content_type="text/plain")
```

---

## Payload types

| Class | Input type | Content-Type |
|---|---|---|
| `BytesPayload` | `bytes`, `bytearray`, `memoryview` | `application/octet-stream` |
| `StringPayload` | `str` | `text/plain; charset=utf-8` |
| `IOBasePayload` | `io.IOBase` | `application/octet-stream` |
| `BytesIOPayload` | `io.BytesIO` | `application/octet-stream` |
| `TextIOPayload` | `io.TextIOBase` | `text/plain; charset=utf-8` |
| `StringIOPayload` | `io.StringIO` | `text/plain; charset=utf-8` |
| `BufferedReaderPayload` | `BufferedReader` | `application/octet-stream` |
| `JsonPayload` | Any (JSON-serializable) | `application/json` |
| `AsyncIterablePayload` | `AsyncIterator[bytes]` | `application/octet-stream` |

### JsonPayload

```python
p = payload.JsonPayload(
    {"key": "value"},
    dumps=json.dumps,
    content_type="application/json",
)
```

### AsyncIterablePayload

For streaming payloads:

```python
async def generate():
    for i in range(10):
        yield f"chunk {i}\n".encode()

p = payload.AsyncIterablePayload(generate())
```

---

## Payload registry

Custom payload factories:

```python
from aiohttp import payload

@payload.payload_type(MyCustomType)
class MyPayload(payload.Payload):
    def __init__(self, value: MyCustomType, *args, **kwargs):
        super().__init__(value, *args, **kwargs)
        self._content_type = "application/x-custom"
```

Or register explicitly:

```python
payload.register_payload(MyPayload, MyCustomType)
```

---

## streamer()

Create a streaming payload from an async generator:

```python
async def data_stream():
    for i in range(100):
        yield f"line {i}\n".encode()

await session.post(url, data=aiohttp.streamer(data_stream()))
```

Equivalent to `AsyncIterablePayload` but more convenient.
