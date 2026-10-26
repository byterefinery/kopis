from kopis import Kopis, DOMEvent, RPCHandle, IS_SERVER, IS_CLIENT


if IS_SERVER:
    print("server 1")
    import os
elif IS_CLIENT:
    print("client 1")
    import sys


k = Kopis()

k.document.head.attach("""
    <script src="//unpkg.com/alpinejs" defer></script>

    <link href="https://cdn.jsdelivr.net/npm/daisyui@5" rel="stylesheet" type="text/css" />
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@5/themes.css" rel="stylesheet" type="text/css" />
""")

k.document.documentElement.setAttribute('data-theme', 'dark')


if k.is_server():
    print("server 2")
    import sys  # noqa: F401 - demo of a side-specific import
elif k.is_client():
    print("client 2")
    import os  # noqa: F401 - demo of a side-specific import


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
async def server_button_click(
    name: str, e: RPCHandle[DOMEvent], point: RPCHandle[Point]
) -> int:
    print("server_button_click", e, point)
    await point.set_xy(-1, -2)
    x, y = point.get_xy()
    print("server_button_click", x, y)

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
    point_h = k.get_handle(point)
    v: int = await k.server_button_click("btn0_click", e_h, point_h)
    print("btn0_click result:", v)

    k.document.body.attach(f"\n{v!s}")


k.document.body.attach("""
    Hello 4 !

    <button id="btn0" class="btn btn-primary">Demo</button>
""")

k.btn0.onclick = btn0_click
k.run()
