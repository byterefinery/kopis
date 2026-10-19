# WebSockets

## Table of Contents

- [WSMsgType](#wsmsgtype)
- [WSCloseCode](#wsclosecode)
- [Server WebSocket](#server-websocket)
- [Client WebSocket](#client-websocket)
- [WebSocket handshake](#websocket-handshake)
- [Heartbeat](#heartbeat)
- [Compression](#compression)
- [Protocols](#protocols)

---

## WSMsgType

WebSocket message types:

| Constant | Description |
|---|---|
| `WSMsgType.TEXT` | Text frame |
| `WSMsgType.BINARY` | Binary frame |
| `WSMsgType.PING` | Ping frame |
| `WSMsgType.PONG` | Pong frame |
| `WSMsgType.CLOSE` | Close frame |
| `WSMsgType.CLOSING` | Connection closing |
| `WSMsgType.ERROR` | Error occurred |

## WSCloseCode

Standard close codes: `NORMAL` (1000), `GOING_AWAY` (1001), `PROTOCOL_ERROR` (1002), `UNSUPPORTED_DATA` (1003), `ABNORMAL_CLOSURE` (1006), `INVALID_FRAME_PAYLOAD_DATA` (1007), `POLICY_VIOLATION` (1008), `MESSAGE_TOO_BIG` (1009), `MANDATORY_EXTENSION` (1010), `INTERNAL_SERVER_ERROR` (1011), `SERVICE_RESTART` (1012), `TRY_AGAIN_LATER` (1013), `BAD_GATEWAY` (1014).

---

## Server WebSocket

`web.WebSocketResponse` handles WebSocket connections on the server side.

### Basic handler

```python
from aiohttp import web, WSMsgType

async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            if msg.data == "close":
                await ws.close()
            else:
                await ws.send_str(f"echo: {msg.data}")
        elif msg.type == WSMsgType.BINARY:
            await ws.send_bytes(f"echo: {msg.data}".encode())
        elif msg.type == WSMsgType.ERROR:
            break

    return ws

app.router.add_get("/ws", ws_handler)
```

### Construction

```python
ws = web.WebSocketResponse(
    timeout=10.0,              # Handshake timeout
    receive_timeout=None,      # Per-message receive timeout
    autoclose=True,            # Auto-close on client disconnect
    autoping=True,             # Auto-respond to pings
    heartbeat=None,            # Heartbeat interval (seconds)
    protocols=(),              # Supported sub-protocols
    compress=True,             # Per-message compression
    max_msg_size=4*1024*1024,  # Max message size (4MB)
    decode_text=True,          # Decode text frames to str
)
```

### Sending messages

```python
await ws.send_str("hello")           # Text
await ws.send_bytes(b"binary")       # Binary
await ws.send_json({"key": "value"}) # JSON (text)
await ws.send_json_bytes(data)       # JSON (bytes)
await ws.ping()                      # Ping
await ws.pong()                      # Unsolicited pong
await ws.send_frame(data, WSMsgType.TEXT)  # Raw frame
```

### Receiving messages

```python
# Iterate (auto-closes on close/error)
async for msg in ws:
    if msg.type == WSMsgType.TEXT:
        print(msg.data)

# Manual receive
msg = await ws.receive()
if msg.type == WSMsgType.TEXT:
    print(msg.data)
elif msg.type == WSMsgType.CLOSE:
    break

# With timeout
msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
```

### Closing

```python
await ws.close(code=1000, message=b"normal close")
```

### Properties

| Property | Type | Description |
|---|---|---|
| `ws.prepared` | `bool` | Handshake completed? |
| `ws.closed` | `bool` | Connection closed? |
| `ws.close_code` | `int \| None` | Close code |
| `ws.ws_protocol` | `str \| None` | Negotiated sub-protocol |
| `ws.compress` | `int \| bool` | Compression active |

### can_prepare check

```python
ready = ws.can_prepare(request)
if not ready.ok:
    return web.HTTPBadRequest(text="Not a WebSocket request")
```

---

## Client WebSocket

`ClientWebSocketResponse` for client-side WebSocket connections.

### Connection

```python
async with session.ws_connect(
    "wss://echo.websocket.org",
    protocols=["chat"],
    heartbeat=15.0,
    compress=15,
    max_msg_size=1024*1024,
) as ws:
    await ws.send_str("hello")
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            print(msg.data)
        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
            break
```

### Construction parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `StrOrURL` | — | WebSocket URL |
| `method` | `str` | `GET` | HTTP method for handshake |
| `protocols` | `Iterable[str]` | `()` | Sub-protocols |
| `timeout` | `ClientWSTimeout` | default | WS timeouts |
| `autoclose` | `bool` | `True` | Auto-close |
| `autoping` | `bool` | `True` | Auto-respond to pings |
| `heartbeat` | `float` | `None` | Heartbeat interval |
| `origin` | `str` | `None` | Origin header |
| `params` | `Query` | `None` | Query parameters |
| `headers` | `LooseHeaders` | `None` | Extra headers |
| `proxy` | `StrOrURL` | `None` | Proxy URL |
| `ssl` | `SSLContext \| bool` | `True` | SSL settings |
| `compress` | `int` | `0` | Compression (0=off, 1-15) |
| `max_msg_size` | `int` | `4MB` | Max message size |
| `decode_text` | `bool` | `True` | Decode text to str |

### Sending

```python
await ws.send_str("hello")
await ws.send_bytes(b"data")
await ws.send_json({"key": "value"})
await ws.ping()
await ws.pong()
```

### Receiving

```python
async for msg in ws:
    ...

msg = await ws.receive()
```

### Closing

```python
await ws.close()
```

### Properties

| Property | Type | Description |
|---|---|---|
| `ws.closed` | `bool` | Connection closed? |
| `ws.close_code` | `int \| None` | Close code |
| `ws.protocol` | `str \| None` | Negotiated protocol |
| `ws.ping_task` | `Task \| None` | Ping task |

---

## WebSocket handshake

The handshake is automatic. Server validates:
- `Upgrade: websocket` header
- `Connection: Upgrade` header
- `Sec-WebSocket-Version: 13`
- Valid `Sec-WebSocket-Key`

On failure, `HTTPBadRequest` is raised (server) or `WSServerHandshakeError` (client).

---

## Heartbeat

Heartbeat sends periodic PING frames and expects PONG responses.

```python
# Server
ws = web.WebSocketResponse(heartbeat=15.0)

# Client
async with session.ws_connect(url, heartbeat=15.0) as ws:
    ...
```

If no PONG is received within `heartbeat / 2` seconds, the connection is closed with `ABNORMAL_CLOSURE`.

---

## Compression

Per-message compression (RFC 7692):

```python
# Server
ws = web.WebSocketResponse(compress=True)

# Client
async with session.ws_connect(url, compress=15) as ws:
    ...
```

`compress=0` disables compression. Values 1-15 set compression level.

---

## Protocols

Sub-protocol negotiation:

```python
# Server — accept "chat" or "binary"
ws = web.WebSocketResponse(protocols=["chat", "binary"])
await ws.prepare(request)
print(ws.ws_protocol)  # "chat" or "binary" or None

# Client — request "chat"
async with session.ws_connect(url, protocols=["chat"]) as ws:
    print(ws.protocol)  # "chat" if agreed
```
