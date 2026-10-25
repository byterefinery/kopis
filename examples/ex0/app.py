from kopis import Kopis, RPCHandle


k = Kopis()


class Point:
    """A type defined in the app, so it exists on both sides. Values are
    pickled and arrive on the other side as real ``Point`` objects."""

    def __init__(self, x: int, y: int) -> None:
        self.x, self.y = x, y

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"


@k.rpc.register
async def server_button_click(name: str, e: RPCHandle, point: Point) -> object:
    print("server_button_click", e, point)

    v = await k.rpc.client_button_click(name, e, point)
    print("server_button_click", v)
    return v


# short way (k.rpc.register is the canonical way)
@k.register
async def client_button_click(name: str, e: RPCHandle, point: Point) -> int:
    # Called by the server. `e` is the same RPCHandle: the live event
    # is in this tab, so it prints as "local", and operations on it
    # run here, with no round trip. `point` is a real Point object (the
    # same class exists on both sides).
    print("client_button_click", name, e, point)
    return 29


async def btn0_click(e: object) -> None:
    print("btn0_click", e)

    # short way for k.rpc.server_button_click(...)
    point = Point(3, 4)
    v = await k.server_button_click("btn0_click", e, point)

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
k["btn0"]["onclick"] = btn0_click

print("k", k)
k.run()
