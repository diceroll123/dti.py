from typing import List, Optional, Union

from .constants import OUTFIT
from .decorators import _require_state
from .enums import LayerImageSize, PetPose
from .errors import InvalidColorSpeciesPair, NoIteratorsFound, OutfitNotFound
from .iterators import (
    DTISearch,
    ItemIDSearch,
    ItemSearch,
    ItemSearchNames,
    ItemSearchToFit,
)
from .models import Color, Neopet, Outfit, Species
from .state import BitField, State


class Client:
    """Represents a client connection that connects to DTI.
    This class is used to interact with the DTI GraphQL API.

    Parameters
    -----------
    cache_timeout: Optional[:class:`int`]
        The amount of time, in seconds, to reload the internal cache. It's updated as-needed after this amount of time.
        Default = 3600 (1 hour).
    """

    __slots__ = ["_state"]

    def __init__(self, cache_timeout: Optional[int] = None):
        self._state = State(cache_timeout=cache_timeout)

    async def invalidate(self):
        """|coro|

        A way to force the internal cache to update."""
        await self._state._update(force=True)

    @_require_state
    async def all_species(self) -> List[Species]:
        """|coro|

        List[:class:`Species`]: Returns a list of all species."""
        return list(self._state._species.values())

    @_require_state
    async def all_colors(self) -> List[Color]:
        """|coro|

        List[:class:`Color`]: Returns a list of all colors."""
        return list(self._state._colors.values())

    @_require_state
    async def get_species(self, name_or_id: Union[int, str]) -> Optional[Species]:
        """|coro|

        Parameters
        -----------
        name_or_id: Union[:class:`int`, :class:`str`]
            The name, or ID of the desired Species. Case-insensitive.

        Returns
        --------
        Optional[:class:`Species`]: Returns a species by name or ID, if it exists. Otherwise returns `None`.
        """
        return self._state._species[name_or_id]

    @_require_state
    async def get_color(self, name_or_id: Union[int, str]) -> Optional[Color]:
        """|coro|

        Parameters
        -----------
        name_or_id: Union[:class:`int`, :class:`str`]
            The name, or ID of the desired Color. Case-insensitive.

        Returns
        --------
        Optional[:class:`Color`]: Returns a color by name or ID, if it exists. Otherwise returns `None`.
        """
        return self._state._colors[name_or_id]

    async def get_bit(
        self,
        *,
        species: Union[int, str, Species],
        color: Union[int, str, Color],
    ) -> BitField:
        """|coro|

        The integer returned from this function represents the currently available pet poses
        for the given species/color combo. While it is the fastest way to check if
        this species/color combo exists, it is definitely not the most straightforward.
        You should query this value by simply using the `check` function.

        Parameters
        -----------
        species: Union[:class:`int`, :class:`str`, :class:`Species`]
            The name, or ID, or Species object of the desired Species. Case-insensitive.
        color: Union[:class:`int`, :class:`str`, :class:`Color`]
            The name, or ID, or Color object of the desired Color. Case-insensitive.

        Returns
        --------
        :class:`BitField`: Returns the bit array field for a given pet species/color.
        """

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        if isinstance(species, Species) and isinstance(color, Color):
            return await self._state._get_bit(species_id=species.id, color_id=color.id)

        return BitField(0)

    async def check(
        self,
        *,
        species: Union[int, str, Species],
        color: Union[int, str, Color],
        pose: Optional[PetPose] = None,
    ) -> bool:
        """|coro|

        A convenience function to get a boolean of a species/color/pose combo existing.

        Parameters
        -----------
        species: Union[:class:`int`, :class:`str`, :class:`Species`]
            The name, or ID, or Species object of the desired Species. Case-insensitive.
        color: Union[:class:`int`, :class:`str`, :class:`Color`]
            The name, or ID, or Color object of the desired Color. Case-insensitive.
        pose: Optional[:class:`PetPose`]
            The desired pet pose. If this value is `None`, this function just checks if the species/color combo exists.

        Returns
        --------
        :class:`bool`: Whether or not this species/color/pose combo exists.
        """

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        if isinstance(species, Species) and isinstance(color, Color):
            return await self._state._check(
                species_id=species.id, color_id=color.id, pose=pose
            )

        return False

    async def fetch_neopet(
        self,
        *,
        species: Union[int, str, Species],
        color: Union[int, str, Color],
        item_names: Optional[List[str]] = None,
        item_ids: Optional[List[Union[str, int]]] = None,
        size: Optional[LayerImageSize] = None,
        pose: Optional[PetPose] = None,
    ) -> Neopet:
        """|coro|

        This function practically creates a DTI outfit directly, by giving the parameters of
        exactly what you want on the pet and how you want it rendered.

        Parameters
        -----------
        species: Union[:class:`int`, :class:`str`, :class:`Species`]
            The name, or ID, or Species object of the desired Species. Case-insensitive.
        color: Union[:class:`int`, :class:`str`, :class:`Color`]
            The name, or ID, or Color object of the desired Color. Case-insensitive.
        item_names: Optional[List[:class:`str`]]
            A list of item names to search for + add to the items of the Neopet.
        item_ids: Optional[List[Union[:class:`str`, :class:`int`]]]
            A list of item IDs to search for + add to the items of the Neopet.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the render. If one is not supplied, it defaults to `LayerImageSize.SIZE_600`.
        pose: Optional[:class:`PetPose`]
            The desired pet pose for the render. If one is not supplied, it may be chosen at random.

        Returns
        --------
        :class:`Neopet`
            The Neopet with the options applied to it.
        """

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        if not isinstance(species, Species) or not isinstance(color, Color):
            raise InvalidColorSpeciesPair("Invalid Species/Color provided")

        return await Neopet._fetch_assets_for(
            species=species,
            color=color,
            item_names=item_names,
            item_ids=item_ids,
            size=size,
            pose=pose or PetPose.ideal(),
            state=self._state,
        )

    async def fetch_neopet_by_name(self, pet_name: str) -> Neopet:
        """|coro|

        Creates a :class:`Neopet` using the name of a real Neopet.

        Parameters
        -----------
        pet_name: :class:`str`
            The name of the pet you'd like to find.

        Raises
        -------
        ~dti.NeopetNotFound
            The Neopet is not found on Neopets.

        Returns
        --------
        :class:`Neopet`
            The corresponding Neopet that matches the name provided.
        """

        return await Neopet._fetch_by_name(pet_name=pet_name, state=self._state)

    @_require_state
    async def fetch_outfit(
        self, outfit_id: int, size: Optional[LayerImageSize] = None
    ) -> Outfit:
        """|coro|

        This function grabs an outfit from DTI by ID.

        Parameters
        -----------
        outfit_id: :class:`int`
            The outfit ID of the outfit on DTI.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the render. If one is not supplied, it defaults to `LayerImageSize.SIZE_600`.

        Raises
        -------
        ~dti.OutfitNotFound
            The Outfit is not found on DTI.

        Returns
        --------
        :class:`Outfit`
            The corresponding outfit that matches the ID.
        """
        data = await self._state._http._query(
            OUTFIT,
            variables={
                "outfitId": outfit_id,
                "size": str(size or LayerImageSize.SIZE_600),
            },
        )

        outfit_data = data["data"]["outfit"]

        if outfit_data is None:
            raise OutfitNotFound(f"Outfit (ID: {outfit_id}) not found.")

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
        per_page: Optional[int] = None,
    ) -> DTISearch:
        """|coro|

        This is a one-size-fits-most search function. Most of the parameters cannot be mixed and matched.

        Parameters
        -----------
        query: Optional[:class:`str`]
            A search query just as you'd type into the search bar on DTI.
        species_id: Optional[:class:`int`]
            The ID of the species you're trying to find items for. Only used when `query` is supplied. If so, this is mandatory.
        color_id: Optional[:class:`int`]
            The ID of the color you're trying to find items for. Only used when `query` is supplied. If so, this is mandatory.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the render. Only used when `query` is supplied. If so, this is optional. If size is not supplied, it defaults to `LayerImageSize.SIZE_600`.
        per_page: Optional[:class:`int`]
            The desired amount of items per results-page. Defaults to 30. Only used when `query` is supplied with `species_id` and `color_id`.
        item_name: Optional[:class:`str`]
            The name of one item to search for. Case sensitive, and must be an exact search. Invalid results will be `None`.
        item_names: Optional[List[:class:`str`]]
            A list of item names to search for. Case sensitive, and must be an exact search. Invalid results will be `None`.
        item_ids: Optional[List[Union[:class:`str`, :class:`int`]]]
            A list of item IDs to search for + add to the items of the Neopet. ***All*** item IDs ***must*** be valid, or :class:`InvalidItemID` will be raised.

        Raises
        -------
        ~dti.InvalidItemID
            An invalid item ID was passed to `item_ids`.

        Returns
        --------
        :class:`.DTISearch`: The async Search iterator
        """

        searcher: Optional[DTISearch] = None
        _names = []

        per_page = per_page or 30

        if item_name:
            _names.append(item_name)

        if item_names:
            _names.extend(item_names)

        if query is not None and species_id is not None and color_id is not None:
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
