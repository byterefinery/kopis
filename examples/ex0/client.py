from kopis import document

from demo0 import f


document <= 'Hello 4 !'  # noqa: B015 (Brython's <= sets element text)


@k.bind
def client_button_click(e):
    print('client_button_click', e)
    return 29


def btn0_click(e):
    # print('btn0_click', e)
    # f('btn0_click', e, e=e)
    k.rpc.server_button_click('btn0_click', e, e=e)


document.querySelector('#btn0').bind('click', btn0_click)
