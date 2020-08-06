import asyncio
from io import BytesIO
from typing import Dict, Optional

import aiohttp


class HTTPClient:
    __slots__ = "extra_kwargs"
    BASE = "https://impress-2020.now.sh"
    API_BASE = f"{BASE}/api"

    def __init__(self, *, proxy=None, proxy_auth=None):
        self.extra_kwargs = {}
        if proxy is not None:
            self.extra_kwargs["proxy"] = proxy
            if proxy_auth is not None:
                self.extra_kwargs["proxy_auth"] = proxy_auth

    async def get_valid_pet_poses(self) -> bytes:
        return await self.get_binary_data(self.API_BASE + "/validPetPoses")

    async def get_binary_data(self, url: str) -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **self.extra_kwargs) as r:
                return await r.content.read()

    async def query(self, query, variables=None, **kwargs) -> Dict:
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
