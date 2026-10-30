from kopis import Kopis, DOMEvent
from kopis.daisyui import Button


k = Kopis()
k.use("tailwindcss")
k.use("daisyui")
k.document.documentElement.setAttribute("data-theme", "dark")


get_count, set_count = k.shared_signal(0)


async def inc_count(e: DOMEvent):
    print("inc_count", e)
    count = await get_count()
    count += 1
    await set_count(count)


async def main(k: Kopis):
    with k.effect():
        with k.document.body:
            btn0 = Button(get_count, class_="btn-primary", onclick=inc_count)
            btn1 = Button(get_count, class_="btn-primary", onclick=inc_count)


k.on_startup.append(main)
k.run()
