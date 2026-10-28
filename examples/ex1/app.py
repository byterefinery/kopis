from kopis import Kopis, DOMEvent, Signal
from kopis.daisyui import Button


k = Kopis()
k.use("tailwindcss")
k.use("daisyui")

k.document.documentElement.setAttribute("data-theme", "dark")


async def count_changed(signal: Signal, new_value: int):
    print("count_changed", new_value)
    for client in k.clients:
        print("client", client)
        await client.update_count()


get_count, set_count = k.signal(0, count_changed)
get_count = k.register(get_count)


async def btn0_click(e: DOMEvent):
    print("btn0_click", e, e.target, e.detail)
    await k.inc_count()


@k.register
async def update_count() -> int:
    # The server's count, put in this side's signal (the server
    # broadcasts it to the clients on every change of the count).
    count = await k.get_count()
    await set_count(count)
    return count


with k.effect():
    with k.document.body:
        Button(get_count, class_="btn-primary", onclick=btn0_click)
        Button(k.get_count, class_="btn-primary", onclick=btn0_click)


@k.register
async def inc_count() -> int:
    count = get_count() + 1
    await set_count(count)
    return count


@k.window.onload
async def window_load(e: DOMEvent):
    print("window_load", e)
    await update_count()


k.run()
