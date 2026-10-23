# Web workers, timers, storage

All of these live in the `browser` package and need `brython_stdlib.js`.

## Web workers (browser.worker)

Run a Python script in a worker thread, keeping the page responsive. Messages are "simple" Python objects (string, number, list, dict with simple items).

The worker script is declared in the page with a dedicated `<script>` tag (the `id` is mandatory):

```xml
<script type="text/python" class="webworker" id="myworker">
# worker program
</script>
```

`src="myworker.py"` can also load the worker script from a file.

Main script side — `create_worker` is asynchronous; `onready` receives the worker object, `onmessage` receives an event whose `data` attribute is the message:

```python
from browser import bind, document, worker

def onmessage(e):
    result.text = e.data

def onready(myworker):
    @bind(inputs, "change")
    def change(evt):
        myworker.send([x.value for x in inputs])

worker.create_worker("myworker", onready, onmessage)
```

`create_worker(worker_id, onready=None, onmessage=None, onerror=None)`; the worker object has a `send(message)` method. Inside a worker, `window` does not exist — `browser.self` represents the worker instead:

```python
from browser import bind, self

@bind(self, "message")
def message(evt):
    ...                    # evt.data holds the message from the main script
    self.send("reply")     # send a message back to the main script
```

A worker cannot access the displayed document (no `document`, no `html` module). The gallery example `www/gallery/webworker_mdn.html` shows a complete worker pair.

## Timers (browser.timer)

```python
from browser import timer

timer.set_interval(func, seconds, *args)     # repeating
timer.set_timeout(func, seconds, *args)      # one shot
timer.clear_interval(id) / timer.clear_timeout(id)
timer.request_animation_frame(func)          # func must take exactly one argument
timer.cancel_animation_frame(id)
timer.set_loop_timeout(seconds)              # cap on how long a blocking loop may run
```

## Local / session storage

`browser.local_storage.storage` and `browser.session_storage.storage` — dict-like, string keys and values, scoped to the origin (scheme, host, port). Local storage persists across browser restarts; session storage is wiped when the browser closes (typical use: a login token).

```python
from browser.local_storage import storage
import json

storage["todo"] = json.dumps([...])          # store any JSON-serializable object
items = json.loads(storage["todo"])          # json turns dict keys into strings
del storage["todo"]                          # raises KeyError afterwards
```

Supports `get`, `pop`, `keys`, `values`, `items`, `clear`, `len`, `in`, iteration; `keys`/`values`/`items` return list copies, not views.

## Other browser APIs

- `browser.indexed_db` — IndexedDB database access
- `browser.websocket` — `supported` boolean and `WebSocket(host)`; bind `open`/`error`/`message` handlers, `message` handler receives a `DOMEvent` with a `data` attribute
- `browser.svg`, `browser.template`, `browser.markdown`, `browser.highlight`
- `browser.widgets.dialog` — e.g. `InfoDialog(title, message, *, top=None, left=None, remove_after=None, ok=False)`
- `browser.widgets.menu`, `browser.webcomponent` — menus and Web Components
- `browser.ui` — building blocks for the built-in widgets (`Border`, `Font`, `Padding`, `Widget`, `Frame`)
