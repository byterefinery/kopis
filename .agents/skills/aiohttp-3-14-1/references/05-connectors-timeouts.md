# Connectors and Timeouts

## Table of Contents

- [TCPConnector](#tcpconnector)
- [UnixConnector](#unixconnector)
- [NamedPipeConnector](#namedpipeconnector)
- [BaseConnector](#baseconnector)
- [Connection](#connection)
- [ClientTimeout](#clienttimeout)
- [SSL and Fingerprint](#ssl-and-fingerprint)
- [Resolvers](#resolvers)

---

## TCPConnector

Primary connector for TCP connections with connection pooling:

```python
connector = aiohttp.TCPConnector(
    limit=100,                  # Max total connections (0 = unlimited)
    limit_per_host=10,          # Max connections per host
    enable_cleanup_closed=True, # Cleanup closed connections (default True)
    force_close=False,          # Close after each request (disables pooling)
    ttl_dns_cache=300,          # DNS cache TTL (seconds)
    use_dns_cache=True,         # Enable DNS caching
    family=socket.AddressFamily.AF_INET,  # Address family
    ssl=None,                   # Default SSL context
    local_addr=("127.0.0.1", 0), # Local address to bind
    resolver=DefaultResolver(), # DNS resolver
    enable_cookies=True,        # Deprecated
    verify_ssl=True,            # Deprecated — use ssl=True/False
    fingerprint=None,           # Deprecated — use ssl=Fingerprint(...)
    ssl_context=None,           # Deprecated — use ssl=context
    ssl_shutdown_timeout=None,  # Deprecated
    happy_eyeballs_delay=0.25,  # Happy Eyeballs delay
    interleave=None,            # Happy Eyeballs interleave
    socket_factory=None,        # Custom socket factory
)
```

### Key parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | `int` | `100` | Max pooled connections |
| `limit_per_host` | `int` | `0` | Max per-host (0 = limit) |
| `force_close` | `bool` | `False` | Disable connection reuse |
| `ttl_dns_cache` | `int` | `300` | DNS cache TTL |
| `use_dns_cache` | `bool` | `True` | DNS caching |
| `local_addr` | `tuple` | `None` | Bind address |
| `resolver` | `AbstractResolver` | `DefaultResolver` | DNS resolver |
| `ssl` | `SSLContext \| bool` | `None` | Default SSL |

### Connection queuing

When `limit` is reached, new requests wait in queue. Use `limit=0` for unlimited connections (not recommended for production).

---

## UnixConnector

Connect via Unix domain sockets:

```python
connector = aiohttp.UnixConnector("/path/to/socket")
session = aiohttp.ClientSession(connector=connector)
```

---

## NamedPipeConnector

Windows named pipes:

```python
connector = aiohttp.NamedPipeConnector(r"\\.\pipe\mypipe")
session = aiohttp.ClientSession(connector=connector)
```

---

## BaseConnector

Abstract base for all connectors. Shared features:

```python
await connector.close()  # Close all connections
connector.closed          # bool — is connector closed?
```

---

## Connection

Represents a single connection from the pool:

```python
# Connection is managed internally by the connector
# Access via response
conn = resp.connection
if conn:
    transport = conn.transport
    protocol = conn.protocol
    conn.close()  # Close this specific connection
```

---

## ClientTimeout

```python
timeout = aiohttp.ClientTimeout(
    total=30,           # Total: request + redirects + response + body read
    connect=10,         # TCP connection establishment
    sock_read=5,        # Socket read (response body)
    sock_connect=5,     # Socket connect
    ceil_threshold=5,   # Timeout granularity floor (prevents tiny timeouts)
)
```

### How timeouts compose

```
total = time from request() call to response body fully read
connect = time to establish TCP connection
sock_read = time between response headers received and body read complete
sock_connect = time for TCP connect() call
```

`total` is the outermost timeout — it covers everything including redirects.

### Per-request timeout

```python
# Override session timeout
resp = await session.get(url, timeout=aiohttp.ClientTimeout(total=5))

# No timeout
resp = await session.get(url, timeout=aiohttp.ClientTimeout(total=None))
```

---

## SSL and Fingerprint

### SSL context

```python
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

session = aiohttp.ClientSession()
resp = await session.get("https://example.com", ssl=ctx)
```

### Disable SSL verification

```python
resp = await session.get("https://example.com", ssl=False)
```

### Certificate fingerprint

```python
# SHA-256 hash of the server certificate
fingerprint = aiohttp.Fingerprint(
    bytes.fromhex("ab:cd:ef:...".replace(":", ""))
)
resp = await session.get("https://example.com", ssl=fingerprint)
```

Only SHA-256 is supported (32 bytes). MD5 and SHA-1 are rejected as insecure.

### SNI (Server Name Indication)

```python
resp = await session.get("https://example.com", server_hostname="example.com")
```

---

## Resolvers

DNS resolution strategies:

```python
# Default — uses asyncio.get_event_loop().resolve_hostname()
resolver = aiohttp.DefaultResolver()

# Threaded — resolves in executor thread
resolver = aiohttp.ThreadedResolver()

# Async — uses aiodns if available
resolver = aiohttp.AsyncResolver()
```

Pass to connector:

```python
connector = aiohttp.TCPConnector(resolver=aiohttp.AsyncResolver())
```
