from typing import List, Optional, Union

from .decorators import _require_state
from .enums import LayerImageSize, PetPose
from .errors import InvalidColorSpeciesPair, NoIteratorsFound
from .iterators import ItemIDSearch, ItemSearch, ItemSearchToFit
from .models import Color, Species
from .neopets import Neopet
from .state import State


class Client:
    __slots__ = "state"

    def __init__(self, cache_timeout: Optional[int] = None):
        self.state = State(cache_timeout=cache_timeout)

    @_require_state
    async def all_species(self) -> List[Species]:
        return list(self.state._species.values())

    @_require_state
    async def all_colors(self) -> List[Color]:
        return list(self.state._colors.values())

    @_require_state
    async def get_species(self, name_or_id: Union[int, str]) -> Optional[Species]:
        return self.state._species[name_or_id]

    @_require_state
    async def get_color(self, name_or_id: Union[int, str]) -> Optional[Color]:
        return self.state._colors[name_or_id]

    async def get_bit(
        self, *, species: Union[int, str, Species], color: Union[int, str, Color],
    ) -> int:

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        return await self.state._get_bit(species_id=species.id, color_id=color.id)

    async def check(
        self,
        *,
        species: Union[int, str, Species],
        color: Union[int, str, Color],
        pose: Optional[PetPose] = None,
    ) -> bool:

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        return await self.state._check(
            species_id=species.id, color_id=color.id, pose=pose
        )

    async def get_neopet(
        self,
        *,
        species: Union[int, str, Species],
        color: Union[int, str, Color],
        item_ids: Optional[List[int]] = None,
        size: Optional[LayerImageSize] = None,
        pose: Optional[PetPose] = None,
    ) -> Neopet:

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        if not species or not color:
            raise InvalidColorSpeciesPair("Invalid Species/Color provided")

        return await Neopet.fetch_assets_for(
            state=self.state,
            species=species,
            color=color,
            item_ids=item_ids,
            size=size,
            pose=pose or PetPose.ideal(),
        )

    async def get_neopet_by_name(self, pet_name) -> Neopet:
        return await Neopet.fetch_by_name(self.state, pet_name)

    def search(
        self,
        *,
        query: Optional[str] = None,
        species_id: Optional[int] = None,
        color_id: Optional[int] = None,
        item_ids: Optional[List[Union[str, int]]] = None,
        size: Optional[LayerImageSize] = None,
        per_page: int = 30,
    ):

        searcher = None

        if all([query, species_id, color_id]):
            searcher = ItemSearchToFit(
                state=self.state,
                query=query,
                species_id=species_id,
                color_id=color_id,
                size=size,
                per_page=per_page,
            )
        elif query:
            searcher = ItemSearch(state=self.state, query=query)
        elif all([item_ids]):
            searcher = ItemIDSearch(state=self.state, item_ids=item_ids)

        if searcher is None:
            raise NoIteratorsFound(
                "None of the values provided matched a search iterator"
            )

        return searcher
