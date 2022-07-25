import asyncio

import aiohttp

from behance_parser.fake_useragent import user_agent


class ImagesLoader:
    def __init__(self, urls: list[str], cookies: list[dict], threads: int = 5) -> None:
        self._threads = threads
        self._urls = urls
        self._cookies = self._build_cookies(cookies)
        self._tmp_result = asyncio.Queue()
        self._tasks = asyncio.Queue()
        self._results = dict()
        for url in urls:
            self._tasks.put_nowait(url)

    @staticmethod
    def _build_cookies(cookies: list[dict[str, str]]):
        cookies_list = [f'{i["name"]}={i["value"]}' for i in cookies]
        return "; ".join(cookies_list)

    async def _load_image(self, url: str) -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=url,
                headers={
                    "user-agent": user_agent.get_random_user_agent(),
                    "cookies": self._cookies,
                },
            ) as response:
                data = await response.read()
                return data

    async def _consumer(self):
        while True:
            url = await self._tasks.get()
            file_data = await self._load_image(url)
            file_name = url.split("/")[-1]
            self._tmp_result.put_nowait((file_name, file_data))
            self._tasks.task_done()

    async def _process(self):
        tasks = []
        for i in range(self._threads):
            task = asyncio.create_task(self._consumer())
            tasks.append(task)

        await self._tasks.join()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def _get_results(self) -> dict[str, bytes]:
        res = dict()
        while not self._tmp_result.empty():
            file_name, file_data = self._tmp_result.get_nowait()
            res[file_name] = file_data
        return res

    def load(self) -> dict[str, bytes]:
        asyncio.run(self._process())
        return self._get_results()
