from kopis import Kopis, DOMEvent, Signal


k = Kopis()
k.use("tailwindcss")
k.use("daisyui")


async def btn0_click(e: DOMEvent):
    print("btn0_click", e, e.detail)
    v: int = await k.inc_count()
    print(f"{v=}")
    k.btn0.innerHTML = v


with k.document.body:
    with k.html.button(id="btn0", class_="btn btn-primary", onclick=btn0_click):
        k.html.text("Demo 1")


async def count_changed(signal: Signal, new_value: int):
    print("count_changed", new_value)

    for client in k.clients:
        await client.update_count()


if k.is_server():
    signal = Signal(0, count_changed)
    get_count, set_count = signal
    get_count = k.register(get_count)

    @k.register
    async def inc_count():
        count = get_count()
        count += 1
        await set_count(count)  # drives the async on_change (the broadcast)
        return count


@k.register
async def update_count():
    print("update_count")
    k.btn0.innerHTML = await k.get_count()


@k.window.onload
async def window_load(e: DOMEvent):
    print("window_load", e)
    await update_count()


k.run()
