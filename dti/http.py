import asyncio
from io import BytesIO
from typing import Dict, Optional

import aiohttp

from .models import AppearanceLayer


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

    async def report_broken_asset(
        self, layer: AppearanceLayer, tries: int = 3, wait_time: float = 3.3
    ) -> Optional[BytesIO]:
        """Reports a broken appearance layer to Dress To Impress, putting it in a queue to be reconverted.

        By default, this will run up to 3 times before returning None. If the layer appears to be fixed, returns the byte data of the image."""

        async with aiohttp.ClientSession() as session:
            await session.post(
                "https://impress.openneo.net/broken_image_reports",
                data={
                    "swf_asset_remote_id": layer.asset_remote_id,
                    "swf_asset_type": layer.asset_type,
                },
                headers={"Referer": "https://impress.openneo.net/"},
                **self.extra_kwargs,
            )
            for _ in range(tries):
                await asyncio.sleep(wait_time)
                async with session.get(layer.image_url) as resp:
                    if resp.status == 200:
                        return BytesIO(await resp.content.read())

        return None

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
