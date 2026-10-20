# from browser import document
from kopis.brython.browser import document


document <= "Hello 4 !"  # noqa: B015 (Brython's <= sets element text)


def btn0_click(e):
    print("btn0_click", e)


document.querySelector("#btn0").bind("click", btn0_click)
