from kopis import Kopis, DOMEvent, Signal
from kopis.daisyui import Button


k = Kopis()
k.use("tailwindcss")
k.use("daisyui")


async def btn0_click(e: DOMEvent):
    print("btn0_click", e, e.detail)
    # v: int = await k.inc_count()
    # print(f"{v=}")
    # e.target.innerHTML = v
    await k.inc_count()


async def count_changed(signal: Signal, new_value: int):
    print("count_changed", new_value)

    for client in k.clients:
        print("client", client)
        # await client.update_count()


signal = Signal(0, count_changed)
get_count, set_count = signal
get_count = k.register(get_count)


with k.document.body:
    Button(get_count, class_="btn-primary", onclick=btn0_click)
    Button(k.get_count, class_="btn-primary", onclick=btn0_click)


@k.register
async def inc_count():
    count = get_count() + 1
    await set_count(count)
    return count


@k.window.onload
async def window_load(e: DOMEvent):
    print("window_load", e)
    # await update_count()


k.run()
