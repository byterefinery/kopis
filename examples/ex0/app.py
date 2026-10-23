from kopis import Kopis, Placeholder, aio

from common import f


k = Kopis(use="brython")


class Point:
    """A type defined in the app, so it exists on both sides. Values are
    pickled and arrive on the other side as real ``Point`` objects."""

    def __init__(self, x, y):
        self.x, self.y = x, y

    def __repr__(self):
        return f"Point({self.x}, {self.y})"


@k.bind
async def server_button_click(name, e, point):
    # Called by the client. `point` arrives as a real Point object (the
    # same class exists on both sides). `e` is a DOM event, which cannot
    # be pickled in the browser, so it arrives as a Placeholder carrying
    # the exception string. Inside this bound function, k.rpc targets
    # the client that called us.
    print("server_button_click", e, point)
    if isinstance(e, Placeholder):
        print("server_button_click: e could not be deserialized:", e.error)
    v = await k.rpc.client_button_click(name, point)
    print("server_button_click", v)
    return v


@k.bind
async def client_button_click(name, point):
    # Called by the server; `point` is a real Point object.
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
