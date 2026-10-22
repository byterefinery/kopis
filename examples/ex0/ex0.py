from kopis import Kopis

from demo0 import f


k = Kopis(use="brython")


@k.bind
async def server_button_click(name, e, point):
    # `e` (a DOM event) and `point` (a client-side type) arrive as plain
    # JSON data; `point` was converted by its to_json() method. Inside
    # this bound function, k.rpc targets the client that called us.
    v = await k.rpc.client_button_click(name, point)
    print('server_button_click', v)
    return v


with k.document.body as el:
    el.append('''
        <button id="btn0">
            Demo
        </button>

        <script type="text/python" src="/client.py"></script>
    ''')


f(k)
k.run()
