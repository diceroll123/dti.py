from typing import Dict

import aiohttp


class HTTPClient:
    __slots__ = "extra_kwargs"
    API_BASE = "https://impress-2020.openneo.net/api"

    def __init__(self, *, proxy=None, proxy_auth=None):
        self.extra_kwargs = {}
        if proxy is not None:
            self.extra_kwargs["proxy"] = proxy
            if proxy_auth is not None:
                self.extra_kwargs["proxy_auth"] = proxy_auth

    async def _fetch_valid_pet_poses(self) -> bytes:
        return await self._fetch_binary_data(self.API_BASE + "/validPetPoses")

    async def _fetch_binary_data(self, url: str) -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **self.extra_kwargs) as r:
                return await r.content.read()

    async def _query(self, query, variables=None, **kwargs) -> Dict:
        # for graphql queries
        kwargs["headers"] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
        }

        # Proxy support
        kwargs.update(self.extra_kwargs)

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.API_BASE}/graphql", json=payload, **kwargs
            ) as r:
                return await r.json()
