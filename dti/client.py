from typing import List, Optional, Union

from .constants import OUTFIT
from .decorators import _require_state
from .enums import LayerImageSize, PetPose
from .errors import InvalidColorSpeciesPair, NoIteratorsFound
from .iterators import ItemIDSearch, ItemSearch, ItemSearchToFit, ItemSearchNames
from .models import Color, Species, Outfit, Neopet
from .state import State


class Client:
    __slots__ = ["_state"]

    def __init__(self, cache_timeout: Optional[int] = None):
        self._state = State(cache_timeout=cache_timeout)

    async def invalidate(self):
        await self._state.update(force=True)

    @_require_state
    async def all_species(self) -> List[Species]:
        return list(self._state._species.values())

    @_require_state
    async def all_colors(self) -> List[Color]:
        return list(self._state._colors.values())

    @_require_state
    async def get_species(self, name_or_id: Union[int, str]) -> Optional[Species]:
        return self._state._species[name_or_id]

    @_require_state
    async def get_color(self, name_or_id: Union[int, str]) -> Optional[Color]:
        return self._state._colors[name_or_id]

    async def get_bit(
        self, *, species: Union[int, str, Species], color: Union[int, str, Color],
    ) -> int:

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        return await self._state._get_bit(species_id=species.id, color_id=color.id)

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

        return await self._state._check(
            species_id=species.id, color_id=color.id, pose=pose
        )

    async def get_neopet(
        self,
        *,
        species: Union[int, str, Species],
        color: Union[int, str, Color],
        item_names: Optional[List[str]] = None,
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
            species=species,
            color=color,
            item_names=item_names,
            item_ids=item_ids,
            size=size,
            pose=pose or PetPose.ideal(),
            state=self._state,
        )

    async def get_neopet_by_name(self, pet_name: str) -> Neopet:
        return await Neopet.fetch_by_name(pet_name=pet_name, state=self._state)

    @_require_state
    async def get_outfit(
        self, outfit_id: int, size: Optional[LayerImageSize] = None
    ) -> Optional[Outfit]:
        data = await self._state.http.query(
            OUTFIT,
            variables={
                "outfitId": outfit_id,
                "size": str(size or LayerImageSize.SIZE_600),
            },
        )

        outfit_data = data["data"]["outfit"]
        if outfit_data:
            return Outfit(**outfit_data, state=self._state)

    def search(
        self,
        *,
        query: Optional[str] = None,
        item_name: Optional[str] = None,
        item_names: Optional[List[str]] = None,
        species_id: Optional[int] = None,
        color_id: Optional[int] = None,
        item_ids: Optional[List[Union[str, int]]] = None,
        size: Optional[LayerImageSize] = None,
        per_page: int = 30,
    ):

        searcher = None
        _names = []

        if item_name:
            _names.append(item_name)

        if item_names:
            _names.extend(item_names)

        if all([query, species_id, color_id]):
            searcher = ItemSearchToFit(
                query=query,
                species_id=species_id,
                color_id=color_id,
                size=size,
                per_page=per_page,
                state=self._state,
            )
        elif _names:
            searcher = ItemSearchNames(names=_names, state=self._state)
        elif query:
            searcher = ItemSearch(query=query, state=self._state)
        elif item_ids:
            searcher = ItemIDSearch(item_ids=item_ids, state=self._state)

        if searcher is None:
            raise NoIteratorsFound(
                "None of the values provided matched a search iterator"
            )

        return searcher
