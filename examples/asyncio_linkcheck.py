import asyncio
import aiohttp
from eliot import start_action, to_file
to_file(open("linkcheck.log", "w"))


async def check_links(urls):
    session = aiohttp.ClientSession()
    with start_action(action_type="check_links", urls=urls):
        for url in urls:
            try:
                with start_action(action_type="download", url=url):
                    async with session.get(url) as response:
                        response.raise_for_status()
            except Exception as e:
                raise ValueError(str(e))

try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        check_links(["http://eliot.readthedocs.io", "http://nosuchurl"])
    )
except ValueError:
    print("Not all links were valid.")
