from kopis import Kopis, DOMEvent


k = Kopis()
k.use("tailwindcss")
k.use("daisyui")

k.document.body.attach("""
    <button id="btn0" class="btn btn-primary">
        Demo 1
    </button>
""")


count = 0


@k.register
def get_count() -> int:
    return count


@k.register
async def inc_count():
    global count
    count += 1
    return count


@k.btn0.onclick
async def btn0_click(e: DOMEvent):
    print("btn0_click", e, e.detail)
    v: int = await k.inc_count()
    print(f"{v=}")
    k.btn0.innerHTML = v


# k.btn0.onclick = btn0_click


@k.window.onload
async def window_load(e: DOMEvent):
    print("window_load", e)
    k.btn0.innerHTML = await k.get_count()


# k.onload = window_load
k.run()
