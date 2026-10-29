from random import randint

from kopis import Kopis, DOMEvent
from kopis.daisyui import Button, List, ListCell, ListRow, Table


k = Kopis()
k.use("tailwindcss")
k.use("daisyui")
k.document.documentElement.setAttribute("data-theme", "dark")


get_count, set_count = k.shared_signal(0)

get_profiles, set_profiles = k.shared_signal([
    {'name': 'John Doe', 'dob': 1970},
    {'name': 'Joe Doe', 'dob': 1971},
])


async def inc_count(e: DOMEvent):
    print("inc_count", e.type)
    count = await get_count()
    count += 1
    await set_count(count)


async def add_new_profile():
    profile = {'name': f'John Doe {randint(0, 100)}', 'dob': 1980 + randint(0, 20)}
    profiles = await get_profiles()
    profiles.append(profile)
    await set_profiles(profiles)


async def main(k: Kopis):
    async with k.effect():
        with k.document.body:
            with k.html.div(class_="m-8 max-w-lg space-y-8"):
                k.html.h1("daisyUI", class_="text-2xl font-bold")

                Button(get_count, color="primary", size="lg", onclick=inc_count)

                List(
                    k.html.li(
                        "Most played songs this week",
                        class_="p-4 pb-2 text-xs opacity-60 tracking-wide",
                    ),
                    ListRow(
                        ListCell("Dio Lupa"),
                        ListCell("Remaining Reason", grow=True),
                        Button("▶", size="xs", style="ghost", modifier="square"),
                    ),
                    ListRow(
                        ListCell("Ellie Beilish"),
                        ListCell("Bears of a fever", grow=True),
                        Button("▶", size="xs", style="ghost", modifier="square"),
                    ),
                )

                with k.html.div(class_="overflow-x-auto"):
                    with Table(size="sm", zebra=True):
                        with k.html.thead():
                            with k.html.tr():
                                k.html.th("#")
                                k.html.th("Name")
                                k.html.th("Job")
                        with k.html.tbody():
                            with k.html.tr():
                                k.html.th("1")
                                k.html.td("Cy Ganderton")
                                k.html.td("Quality Control Specialist")
                            with k.html.tr(class_="row-hover"):
                                k.html.th("2")
                                k.html.td("Jeson Wilky")
                                k.html.td("Commercial Interaction Lead")

                with k.html.div(class_="overflow-x-auto"):
                    with Table(size="sm", zebra=True):
                        with k.html.thead():
                            with k.html.tr():
                                k.html.th("#")
                                k.html.th("Name")
                                k.html.th("DOB")

                        with k.html.tbody():
                            i = 1

                            async for profile in get_profiles():
                                with k.html.tr():
                                    k.html.th(str(i))
                                    k.html.td(profile['name'])
                                    k.html.td(profile['dob'])

                                i += 1


k.on_startup.append(main)
k.run()
