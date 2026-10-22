from kopis import Kopis, document, aio

from common import f


k = Kopis(use="brython")

document <= 'Hello 4 !'  # noqa: B015 (Brython's <= sets element text)


class Point:
    """A client-side-only type, serialized to plain JSON via to_json()."""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def to_json(self):
        return {'x': self.x, 'y': self.y}


@k.bind
async def client_button_click(name: str, point: Point):
    # Called by the server; `point` is plain data ({"x":..., "y":...}).
    print('client_button_click', name, point)
    return 29


def btn0_click(e):
    print('btn0_click', e)
    f('btn0_click', e, e=e)

    async def roundtrip():
        v = await k.rpc.server_button_click('btn0_click', e, Point(3, 4))
        print('btn0_click result:', v)
        document <= f'\n{v!s}'  # noqa: B015 (Brython's <= sets element text)
        return v

    v = aio.run(roundtrip())
    print('btn0_click end', v)


document.querySelector('#btn0').bind('click', btn0_click)
