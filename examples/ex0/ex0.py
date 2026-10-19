from kopis import Kopis

k = Kopis()

k.document = '''
<html>
    <head>
        <meta charset="utf-8">
        <script type="text/javascript" src="brython.js"></script>
        <script type="text/javascript" src="brython_stdlib.js"></script>
    </head>

    <body>
        <script type="text/python">
          from browser import document
          document <= "Hello 2 !"
        </script>
    </body>
</html>
'''

k.run()
