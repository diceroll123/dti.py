import asyncio
from typing import List, Optional, Union

from .constants import SEARCH_ITEM_IDS, SEARCH_QUERY, SEARCH_TO_FIT
from .enums import LayerImageSize
from .models import Item
from .state import State


class _DTISearch:
    # this is a base class
    def __init__(self, state: State, per_page: Optional[int] = None):
        self.state = state
        self._items = asyncio.Queue(maxsize=per_page or 0)
        self._exhausted = False

    async def fetch_items(self):
        raise NotImplementedError

    def post_fetch(self, items: List[Item]):
        # override these where needed to do things like adding to offset
        # this here, by default, will exhaust the searcher, with single-offset searchers in mind
        self._exhausted = True

    async def _fill_items(self):
        items = await self.fetch_items()

        for item in items:
            await self._items.put(Item(**item))

        self.post_fetch(items)

    def __aiter__(self):
        return self

    async def flatten(self):
        ret = []
        while True:
            try:
                item = await self.next()
            except StopAsyncIteration:
                return ret
            else:
                ret.append(item)

    async def next(self):
        if self._items.empty() and not self._exhausted:
            await self._fill_items()

        try:
            return self._items.get_nowait()
        except asyncio.QueueEmpty:
            raise StopAsyncIteration

    async def __anext__(self):
        return await self.next()


class ItemIDSearch(_DTISearch):
    # an item-ID search
    # this WILL crash if you search an item ID that doesn't correspond to an item in the database
    # TODO: might need to be tweaked to be paginated in the future
    def __init__(self, state: State, item_ids: List[Union[str, int]]):
        super().__init__(state)
        self.item_ids = item_ids

    async def fetch_items(self):
        data = await self.state.http.query(
            query=SEARCH_ITEM_IDS, variables={"itemIds": self.item_ids},
        )
        return data["data"]["items"]


class _PaginatedDTISearch(_DTISearch):
    async def fetch_items(self):
        raise NotImplementedError

    def post_fetch(self, items: List[Item]):
        self.offset += self.per_page

        # when we find the last page, don't try another next time
        self._exhausted = len(items) < self.per_page


class ItemSearchToFit(_PaginatedDTISearch):
    # a regular search query that fits the species/color given
    def __init__(
        self,
        state: State,
        *,
        query: str,
        species_id: int,
        color_id: int,
        per_page: int = 30,
        size: Optional[LayerImageSize] = None
    ):
        super().__init__(state, per_page=per_page)
        self.query = query
        self.species_id = species_id
        self.color_id = color_id
        self.offset = 0
        self.per_page = per_page
        self.size = size

    async def fetch_items(self):
        data = await self.state.http.query(
            query=SEARCH_TO_FIT,
            variables={
                "query": self.query,
                "speciesId": self.species_id,
                "colorId": self.color_id,
                "offset": self.offset,
                "limit": self.per_page,
                "size": str(self.size or LayerImageSize.SIZE_600),
            },
        )
        return data["data"]["itemSearchToFit"]["items"]


class ItemSearch(_DTISearch):
    # a regular search query
    def __init__(self, state: State, *, query: str):
        super().__init__(state)
        self.query = query

    async def fetch_items(self):
        data = await self.state.http.query(
            query=SEARCH_QUERY, variables={"query": self.query},
        )
        return data["data"]["itemSearch"]["items"]
