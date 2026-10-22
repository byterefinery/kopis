from kopis import Kopis, aio

from common import f


k = Kopis(use="brython")


class Point:
    """A client-side type, serialized to plain JSON via to_json()."""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def to_json(self):
        return {"x": self.x, "y": self.y}


@k.bind
async def server_button_click(name, e, point):
    # Called by the client; `e` (a DOM event) and `point` (a client-side
    # type) arrive as plain JSON data; `point` was converted by its
    # to_json() method. Inside this bound function, k.rpc targets the
    # client that called us.
    v = await k.rpc.client_button_click(name, point)
    print("server_button_click", v)
    return v


@k.bind
async def client_button_click(name, point):
    # Called by the server; `point` is plain data ({"x": ..., "y": ...}).
    print("client_button_click", name, point)
    return 29


def btn0_click(e):
    print("btn0_click", e)
    f("btn0_click", e, e=e)

    async def roundtrip():
        v = await k.rpc.server_button_click("btn0_click", e, Point(3, 4))
        print("btn0_click result:", v)
        k.document <= f"\n{v!s}"  # noqa: B015 (<= appends to the document)
        return v

    v = aio.run(roundtrip())
    print("btn0_click end", v)


k.document <= "Hello 4 !"  # noqa: B015 (<= appends to the document)

with k.document.body as el:
    el.append('<button id="btn0">Demo</button>')

k.document.querySelector("#btn0").bind("click", btn0_click)  # ty: ignore[unresolved-attribute]

f(k)
k.run()
