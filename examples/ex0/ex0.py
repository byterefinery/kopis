from kopis import Kopis


k = Kopis(use='brython')


with k.document.body as el:
    el.add('''
        <button id="btn0">
            Demo
        </button>

        <script type="text/python" src="/client.py"></script>
    ''')


k.run()
