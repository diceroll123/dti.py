from typing import Dict, Optional

import httpx


class HTTPClient:
    __slots__ = ("_proxy",)
    API_BASE = "https://impress-2020.openneo.net/api"

    def __init__(self, *, proxy: Optional[str] = None):
        self._proxy = proxy

    async def _fetch_valid_pet_poses(self) -> bytes:
        return await self._fetch_binary_data(self.API_BASE + "/validPetPoses")

    async def _fetch_binary_data(self, url: str) -> bytes:
        async with httpx.AsyncClient(
            proxies=self._proxy, transport=httpx.AsyncHTTPTransport(retries=3)
        ) as client:
            response = await client.get(url)
            return response.read()

    async def _query(self, query, variables=None, **kwargs) -> Dict:
        # for graphql queries
        kwargs["headers"] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(
            proxies=self._proxy, transport=httpx.AsyncHTTPTransport(retries=3)
        ) as client:
            response = await client.post(
                f"{self.API_BASE}/graphql", json=payload, **kwargs
            )
            return response.json()
