from kopis import Kopis, Placeholder


k = Kopis()


class Point:
    """A type defined in the app, so it exists on both sides. Values are
    pickled and arrive on the other side as real ``Point`` objects."""

    def __init__(self, x: int, y: int) -> None:
        self.x, self.y = x, y

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"


@k.rpc.register
async def server_button_click(name: str, e: object, point: Point) -> object:
    # Called by the client. `point` arrives as a real Point object (the
    # same class exists on both sides). `e` is a DOM event, which cannot
    # be pickled in the browser, so it arrives as a Placeholder carrying
    # the exception string. Inside this registered function, k.rpc
    # targets the client that called us.
    print("server_button_click", e, point)

    if isinstance(e, Placeholder):
        print("server_button_click: e could not be deserialized:", e.error)

    v = await k.rpc.client_button_click(name, point)
    print("server_button_click", v)
    return v


# short way (k.rpc.register is the canonical way)
@k.register
async def client_button_click(name: str, point: Point) -> int:
    # Called by the server; `point` is a real Point object.
    print("client_button_click", name, point)
    return 29


async def btn0_click(e: object) -> None:
    print("btn0_click", e)

    # short way for k.rpc.server_button_click(...)
    v = await k.server_button_click("btn0_click", e, Point(3, 4))

    print("btn0_click result:", v)
    k.document.body.attach(f"\n{v!s}")


k.document.body.attach("""
    Hello 4 !

    <button id="btn0">Demo</button>
""")

# Bind the click handler of btn0. All three lines are equivalent:
#
#   k.document["btn0"].addEventListener("click", btn0_click)
#   k.document["btn0"]["onclick"] = btn0_click
#   k["btn0"]["onclick"] = btn0_click
#
# (k["btn0"] is k.document["btn0"], the element with id "btn0"; a
# coroutine handler is started with aio.run, so await works inside it.)
k["btn0"]["onclick"] = btn0_click

print("k", k)
k.run()
