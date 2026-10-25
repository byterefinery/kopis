from kopis import Kopis, DOMEvent, RPCHandle


k = Kopis()


class Point:
    """A type defined in the app, so it exists on both sides. Values are
    pickled and arrive on the other side as real ``Point`` objects."""

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"

    def get_xy(self) -> tuple[int, int]:
        return self.x, self.y

    async def set_xy(self, x: int, y: int):
        self.x = x
        self.y = y


@k.register
async def server_button_click(name: str, e: RPCHandle[DOMEvent], point: Point) -> int:
    print("server_button_click", e, point)
    await point.set_xy(-1, -2)
    print("server_button_click", point.get_xy())

    v: int = await k.client_button_click(name, e, point)
    print("server_button_click", v)
    return v


@k.register
async def client_button_click(name: str, e: DOMEvent, point: Point) -> int:
    print("client_button_click", name, e, point)
    return 29


async def btn0_click(e: DOMEvent):
    print("btn0_click", e)
    point = Point(3, 4)

    e_h = k.get_handle(e)
    v: int = await k.server_button_click("btn0_click", e_h, point)
    print("btn0_click result:", v)

    k.document.body.attach(f"\n{v!s}")


k.document.body.attach("""
    Hello 4 !

    <button id="btn0">Demo</button>
""")

k.btn0.onclick = btn0_click
k.run()
