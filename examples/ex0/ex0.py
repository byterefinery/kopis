from kopis import Kopis

from demo0 import f


k = Kopis(use="brython")


def server_button_click(e):
    print('server_button_click', e)
    return 23


with k.document.body as el:
    el.append("""
        <button id="btn0">
            Demo
        </button>

        <script type="text/python" src="/client.py"></script>
    """)


f(k)
k.run()
