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
    # Called by the client. `point` arrives as a real Point object (the
    # same class exists on both sides). `e` is a DOM event, which cannot
    # be pickled in the browser: the event stays alive in the browser,
    # and an RPCHandle pointing at it arrives here instead — the same
    # wrap that k.handle does. Printing it needs no round trip: the
    # browser computed the event's true repr when the handle was made,
    # and it came with the handle.
    print("server_button_click", e, point)

    # Operations on the handle are sent to the browser, where the live
    # event performs them and the result comes back.
    print("event type:", await e.type)
    target = await e.target  # the live button element: another handle
    print("target:", target)
    print("target id:", await target.id)

    # Mutations are fire and forget: the owner applies them to the live
    # object, and no result comes back.
    target["data-kopis"] = "visited"

    # Methods work the same way: the live object is called there, and
    # the result comes back.
    print("has data-kopis:", await target.hasAttribute("data-kopis"))

    # k.get_handle makes an explicit handle to any object, picklable or
    # not: the handle can be sent on, in either direction. This one —
    # to the live Point — goes to the client, where operations on it
    # come back here.
    p = k.get_handle(point)
    v = await k.rpc.client_button_click(name, e, p)
    print("server_button_click", v)
    return v


# short way (k.rpc.register is the canonical way)
@k.register
async def client_button_click(name: str, e: RPCHandle, p: RPCHandle) -> int:
    # Called by the server. `e` is the same RPCHandle: the live event
    # is in this tab, so it prints as "local", and operations on it
    # run here, with no round trip. `p` is the server's handle to the
    # live Point: it prints as "remote", and reading it goes to the
    # server.
    print("client_button_click", name, e, p, await e.type, await p.x)
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
