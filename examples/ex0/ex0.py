from kopis import Kopis

from demo0 import f


k = Kopis(use="brython")


with k.document.body as el:
    el.append("""
        <button id="btn0">
            Demo
        </button>

        <script type="text/python" src="/client.py"></script>
    """)


f(k)
k.run()
