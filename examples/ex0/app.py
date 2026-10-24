from kopis import Kopis, Placeholder, aio

k = Kopis()


class Point:
    """A type defined in the app, so it exists on both sides. Values are
    pickled and arrive on the other side as real ``Point`` objects."""

    def __init__(self, x: int, y: int) -> None:
        self.x, self.y = x, y

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"


@k.rpc.register  # canonical way (k.register is the short way)
async def server_button_click(name: str, e: object, point: Point) -> object:
    # Called by the client. `point` arrives as a real Point object (the
    # same class exists on both sides). `e` is a DOM event, which cannot
    # be pickled in the browser, so it arrives as a Placeholder carrying
    # the exception string. Inside this registered function, k.rpc
    # targets the client that called us.
    print("server_button_click", e, point)
    if isinstance(e, Placeholder):
        print("server_button_click: e could not be deserialized:", e.error)
    v = await k.rpc.client_button_click(name, point)  # canonical way
    print("server_button_click", v)
    return v


@k.register  # short way (k.rpc.register is the canonical way)
async def client_button_click(name: str, point: Point) -> int:
    # Called by the server; `point` is a real Point object.
    print("client_button_click", name, point)
    return 29


def btn0_click(e: object) -> None:
    print("btn0_click", e)

    async def roundtrip() -> None:
        v = await k.server_button_click(
            "btn0_click", e, Point(3, 4)
        )  # short way for k.rpc.server_button_click(...)
        print("btn0_click result:", v)
        k.document <= f"\n{v!s}"  # noqa: B015 (<= appends to the document)

    aio.run(roundtrip())


k.document <= "Hello 4 !"  # noqa: B015 (<= appends to the document)

with k.document.body as el:
    el.append('<button id="btn0">Demo</button>')

k.document.querySelector("#btn0").addEventListener("click", btn0_click)  # ty: ignore[unresolved-attribute]

print("k", k)

k.run()
