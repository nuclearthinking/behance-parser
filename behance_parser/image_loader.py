import asyncio

import aiohttp

from behance_parser.fake_useragent import user_agent

_cookies: list[dict] | None = None


def _build_cookie(cookies: list[dict]) -> str:
    _cookie = [f'{i["name"]}={i["value"]}' for i in cookies]
    return "; ".join(_cookie)


async def _load_image(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url=url,
            headers={
                "user-agent": user_agent.get_random_user_agent(),
                "cookies": _build_cookie(cookies=_cookies),
            },
        ) as response:
            data = await response.read()
            return data


async def _load_images_async(urls: list[str]) -> dict[str, bytes]:
    queue = asyncio.Queue()
    result = asyncio.Queue()

    for url in urls:
        queue.put_nowait(url)

    async def consumer():
        while True:
            url = await queue.get()
            file_data = await _load_image(url)
            file_name = url.split("/")[-1]
            result.put_nowait((file_name, file_data))
            queue.task_done()

    tasks = []
    for i in range(5):
        task = asyncio.create_task(consumer())
        tasks.append(task)

    await queue.join()
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def load_images(urls: list[str], cookies: list[dict]) -> dict[str, bytes]:
    global _cookies
    _cookies = cookies
    result: dict[str, bytes] | None = None

    async def main():
        nonlocal result
        result = await _load_images_async(urls)

    asyncio.run(main())
    return result
