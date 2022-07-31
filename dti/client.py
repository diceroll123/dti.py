from __future__ import annotations

import copy
from collections import defaultdict
from typing import DefaultDict

from dti.types import (
    CanonicalAppearancePayload,
    FetchAllAppearancesPayload,
    ItemAllAppearancesPayload,
    ItemAppearancePayload,
    OutfitPayload,
    PetAppearancePayload,
    ZonePayload,
)

from .enums import ItemKind, LayerImageSize, PetPose
from .errors import (
    InvalidColor,
    InvalidColorSpeciesPair,
    InvalidSpecies,
    NoIteratorsFound,
)
from .iterators import (
    DTISearch,
    ItemIDSearch,
    ItemSearch,
    ItemSearchNames,
    ItemSearchToFit,
)
from .models import Color, Item, Neopet, Outfit, PetAppearance, Species, Zone
from .state import BitField, State

__all__: tuple[str, ...] = (
    "Client",
)


class Client:
    """Represents a client connection that connects to DTI.
    This class is used to interact with the DTI GraphQL API.

    Parameters
    -----------
    cache_timeout: Optional[:class:`int`]
        The amount of time, in seconds, to reload the internal cache. It's updated as-needed after this amount of time.
        Default = 3600 (1 hour).
    proxy: Optional[:class:`str`]
        Proxy URL. If you have credentials, pass them in like so: "http://username:password@localhost:8030"
    """

    __slots__: tuple[str, ...] = ("_state",)

    def __init__(
        self, cache_timeout: int | None = None, proxy: str | None = None
    ) -> None:
        self._state = State(cache_timeout=cache_timeout, proxy=proxy)

    async def invalidate(self) -> None:
        """|coro|

        A way to force the internal cache to update."""
        await self._state._update(force=True)  # type: ignore

    async def all_species(self) -> list[Species]:
        """|coro|

        List[:class:`Species`]: Returns a list of all species."""
        await self._state._lock_and_update()  # type: ignore
        return list(self._state._species.values())  # type: ignore

    async def all_colors(self) -> list[Color]:
        """|coro|

        List[:class:`Color`]: Returns a list of all colors."""
        await self._state._lock_and_update()  # type: ignore
        return list(self._state._colors.values())  # type: ignore

    async def get_species(self, name_or_id: int | str, /) -> Species:
        """|coro|

        Parameters
        -----------
        name_or_id: Union[:class:`int`, :class:`str`]
            The name, or ID of the desired Species. Case-insensitive.

        Raises
        -------
        ~dti.InvalidSpecies
            The species does not exist.

        Returns
        --------
        :class:`Species`: Returns a species by name or ID.
        """
        await self._state._lock_and_update()  # type: ignore
        species: Species | None = self._state._species[name_or_id]  # type: ignore
        if species is None:
            raise InvalidSpecies()
        return species

    async def get_color(self, name_or_id: int | str, /) -> Color:
        """|coro|

        Parameters
        -----------
        name_or_id: Union[:class:`int`, :class:`str`]
            The name, or ID of the desired Color. Case-insensitive.

        Raises
        -------
        ~dti.InvalidColor
            The color does not exist.

        Returns
        --------
        :class:`Color`: Returns a color by name or ID.
        """
        await self._state._lock_and_update()  # type: ignore
        color: Color | None = self._state._colors[name_or_id]  # type: ignore
        if color is None:
            raise InvalidColor()
        return color

    async def get_bit(
        self,
        *,
        species: int | str | Species,
        color: int | str | Color,
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

        Raises
        -------
        ~dti.InvalidColor
            The color does not exist.
        ~dti.InvalidSpecies
            The species does not exist.

        Returns
        --------
        :class:`BitField`: Returns the bit array field for a given pet species/color.
        """

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        return await self._state._get_bit(species_id=species.id, color_id=color.id)  # type: ignore

    async def check(
        self,
        *,
        species: int | str | Species,
        color: int | str | Color,
        pose: PetPose | None = None,
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

        Raises
        -------
        ~dti.InvalidColor
            The color does not exist.
        ~dti.InvalidSpecies
            The species does not exist.

        Returns
        --------
        :class:`bool`: Whether or not this species/color/pose combo exists.
        """

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        return await self._state._check(  # type: ignore
            species_id=species.id, color_id=color.id, pose=pose
        )

    async def fetch_neopet(
        self,
        *,
        species: int | str | Species,
        color: int | str | Color,
        item_names: list[str] | None = None,
        item_ids: list[int] | None = None,
        size: LayerImageSize | None = None,
        pose: PetPose | None = None,
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
        item_ids: Optional[List[:class:`int`]]
            A list of item IDs to search for + add to the items of the Neopet.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the render. If one is not supplied, it defaults to `LayerImageSize.SIZE_600`.
        pose: Optional[:class:`PetPose`]
            The desired pet pose for the render. If one is not supplied, it may be chosen at random.

        Raises
        -------
        ~dti.InvalidColor
            The color does not exist.
        ~dti.InvalidSpecies
            The species does not exist.
        ~dti.InvalidColorSpeciesPair
            This species/color/pose combo does not exist, according to DTI.

        Returns
        --------
        :class:`Neopet`
            The Neopet with the options applied to it.
        """

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        valid = await self.check(species=species, color=color, pose=pose)

        if not valid:
            raise InvalidColorSpeciesPair("Invalid Species/Color/Pose provided")

        return await Neopet._fetch_assets_for(  # type: ignore
            species=species,
            color=color,
            item_names=item_names,
            item_ids=item_ids,
            size=size,
            pose=pose or PetPose.ideal(),
            state=self._state,
        )

    async def fetch_neopet_by_name(
        self, pet_name: str, /, size: LayerImageSize | None = None
    ) -> Neopet:
        """|coro|

        Creates a :class:`Neopet` using the name of a real Neopet.

        Parameters
        -----------
        pet_name: :class:`str`
            The name of the pet you'd like to find.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the render. If one is not supplied, it defaults to `LayerImageSize.SIZE_600`.

        Raises
        -------
        ~dti.NeopetNotFound
            The Neopet is not found on Neopets.

        Returns
        --------
        :class:`Neopet`
            The corresponding Neopet that matches the name provided.
        """

        size = size or LayerImageSize.SIZE_600

        return await Neopet._fetch_by_name(  # type: ignore
            pet_name=pet_name, size=size, state=self._state
        )

    async def fetch_outfit(
        self, outfit_id: int, /, size: LayerImageSize | None = None
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

        await self._state._lock_and_update()  # type: ignore

        size = size or LayerImageSize.SIZE_600

        data: OutfitPayload = await self._state.http.fetch_outfit(
            id=outfit_id, size=size
        )

        return Outfit(data=data, size=size, state=self._state)

    def search(
        self,
        *,
        query: str | None = None,
        item_name: str | None = None,
        item_names: list[str] | None = None,
        item_kind: ItemKind | None = None,
        species_id: int | None = None,
        color_id: int | None = None,
        item_ids: list[int] | None = None,
        size: LayerImageSize | None = None,
        per_page: int | None = None,
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
        item_kind: Optional[:class:`ItemKind`]
            The desired kind of item you're trying to find. Can significantly reduce your search query.
        per_page: Optional[:class:`int`]
            The desired amount of items per results-page. Defaults to 30. Only used when `query` is supplied with `species_id` and `color_id`.
        item_name: Optional[:class:`str`]
            The name of one item to search for. Case sensitive, and must be an exact search. Invalid results will be `None`.
        item_names: Optional[List[:class:`str`]]
            A list of item names to search for. Case sensitive, and must be an exact search. Invalid results will be `None`.
        item_ids: Optional[List[:class:`int`]]
            A list of item IDs to search for + add to the items of the Neopet. ***All*** item IDs ***must*** be valid, or :class:`InvalidItemID` will be raised.

        Raises
        -------
        ~dti.InvalidItemID
            An invalid item ID was passed to `item_ids`.

        Returns
        --------
        :class:`.DTISearch`: The async Search iterator
        """

        searcher: DTISearch | None = None
        _names: list[str] = []

        per_page: int = per_page or 30

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
                item_kind=item_kind,
                per_page=per_page,
                state=self._state,
            )
        elif _names:
            searcher = ItemSearchNames(names=_names, state=self._state)
        elif query:
            searcher = ItemSearch(query=query, item_kind=item_kind, state=self._state)
        elif item_ids:
            searcher = ItemIDSearch(item_ids=item_ids, state=self._state)

        if searcher is None:
            raise NoIteratorsFound(
                "None of the values provided matched a search iterator"
            )

        return searcher

    async def fetch_appearance(
        self,
        *,
        species: int | str | Species,
        color: int | str | Color,
        pose: PetPose,
        size: LayerImageSize | None = None,
    ) -> PetAppearance:
        """|coro|

        Fetches the pet appearance of a provided species/color/pose.

        Parameters
        -----------
        species: Union[:class:`int`, :class:`str`, :class:`Species`]
            The name, or ID, or Species object of the desired Species. Case-insensitive.
        color: Union[:class:`int`, :class:`str`, :class:`Color`]
            The name, or ID, or Color object of the desired Color. Case-insensitive.
        pose: :class:`PetPose`
            The desired pet pose for the appearance.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the pet appearance image layers. If one is not supplied, it defaults to `LayerImageSize.SIZE_600`.

        Raises
        -------
        ~dti.InvalidColor
            The color does not exist.
        ~dti.InvalidSpecies
            The species does not exist.
        ~dti.InvalidColorSpeciesPair
            This species/color combo does not exist, according to DTI.
        ~dti.MissingPetAppearance
            The Pet Appearance is not found on DTI.

        Returns
        --------
        :class:`PetAppearance`
            The corresponding pet appearance.
        """

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        valid: bool = await self.check(species=species, color=color, pose=pose)

        if not valid:
            raise InvalidColorSpeciesPair("Invalid Species/Color/Pose provided")

        size = size or LayerImageSize.SIZE_600

        data: PetAppearancePayload = await self._state.http.fetch_appearance(
            species=species, color=color, pose=pose, size=size
        )

        return PetAppearance(data=data, size=size, state=self._state)

    async def fetch_appearance_by_id(
        self, appearance_id: int, /, size: LayerImageSize | None = None
    ) -> PetAppearance:
        """|coro|

        Fetches the pet appearance from DTI by ID, if it exists.

        Parameters
        -----------
        appearance_id: :class:`int`
            The appearance ID you'd like.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the pet appearance image layers. If one is not supplied, it defaults to `LayerImageSize.SIZE_600`.

        Raises
        -------
        ~dti.MissingPetAppearance
            The Pet Appearance is not found on DTI.

        Returns
        --------
        :class:`PetAppearance`
            The corresponding pet appearance.
        """
        size = size or LayerImageSize.SIZE_600

        data: PetAppearancePayload = await self._state.http.fetch_appearance_by_id(
            id=appearance_id, size=size
        )

        return PetAppearance(data=data, size=size, state=self._state)

    async def fetch_appearances(
        self,
        *,
        species: int | str | Species,
        color: int | str | Color,
        size: LayerImageSize | None = None,
    ) -> list[PetAppearance]:
        """|coro|

        Fetches pet appearances of a provided species/color.

        Parameters
        -----------
        species: Union[:class:`int`, :class:`str`, :class:`Species`]
            The name, or ID, or Species object of the desired Species. Case-insensitive.
        color: Union[:class:`int`, :class:`str`, :class:`Color`]
            The name, or ID, or Color object of the desired Color. Case-insensitive.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the pet appearance layers. If one is not supplied, it defaults to `LayerImageSize.SIZE_600`.

        Raises
        -------
        ~dti.InvalidColor
            The color does not exist.
        ~dti.InvalidSpecies
            The species does not exist.
        ~dti.InvalidColorSpeciesPair
            This species/color combo does not exist, according to DTI.

        Returns
        --------
        List[:class:`PetAppearance`]
            The list of this pet's appearances.
        """

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        valid: bool = await self.check(species=species, color=color)

        if not valid:
            raise InvalidColorSpeciesPair("Invalid Species/Color provided")

        size = size or LayerImageSize.SIZE_600

        data: list[PetAppearancePayload] = await self._state.http.fetch_appearances(
            species=species, color=color, size=size
        )

        return [PetAppearance(data=d, size=size, state=self._state) for d in data]

    async def fetch_all_zones(self) -> list[Zone]:
        """|coro|

        Fetches all appearance zones for a customization.

        Returns
        --------
        List[:class:`Zone`]
            A list of all Zones.
        """
        data: list[ZonePayload] = await self._state.http.fetch_all_zones()
        return [Zone(data=d) for d in data]

    async def fetch_appearance_ids(
        self,
        *,
        species: int | str | Species,
        color: int | str | Color,
    ) -> list[int]:
        """|coro|

        Fetches all appearance ids for a given species+color.

        Raises
        -------
        ~dti.InvalidColor
            The color does not exist.
        ~dti.InvalidSpecies
            The species does not exist.
        ~dti.InvalidColorSpeciesPair
            This species/color combo does not exist, according to DTI.

        Returns
        --------
        List[:class:`int`]
            A list of the pet appearance IDs.
        """

        if not isinstance(species, Species):
            species = await self.get_species(species)

        if not isinstance(color, Color):
            color = await self.get_color(color)

        valid: bool = await self.check(species=species, color=color)

        if not valid:
            raise InvalidColorSpeciesPair("Invalid Species/Color/Pose provided")

        return await self._state.http.fetch_appearance_ids(species=species, color=color)

    async def fetch_all_appearances(
        self,
        *,
        item_id: int | None = None,
        item_ids: list[int] | None = None,
        color: int | str | Color | None = None,
        size: LayerImageSize | None = None,
    ) -> list[Neopet]:

        _item_ids: list[int] = []

        if item_id:
            _item_ids.append(item_id)

        if item_ids:
            _item_ids.extend(item_ids)

        if color is not None and not isinstance(color, Color):
            color = await self.get_color(color)

        if not isinstance(color, Color):
            # DTI falls back to Blue, so we will as well!
            color = await self.get_color("Blue")

        size = size or LayerImageSize.SIZE_600

        data: FetchAllAppearancesPayload = (
            await self._state.http.fetch_all_appearances_for_color(
                color, item_ids=_item_ids, size=size
            )
        )
        all_pet_appearances: list[CanonicalAppearancePayload] = data["color"].get(
            "appliedToAllCompatibleSpecies"
        )

        all_items: list[ItemAllAppearancesPayload] = data.get("items", [])
        item_map: DefaultDict[int, list[Item]] = defaultdict(list)  # bodyId, [Item]
        return_neopets: list[Neopet] = []

        for item in all_items:
            item_appearances: list[ItemAppearancePayload] = item.get("allAppearances")
            # won't be needing that in there anymore
            # the rest of this object is now just an Item
            real_item = Item(data=item, state=self._state)  # type: ignore

            for item_appearance in item_appearances:
                # please forgive me
                body_id = int(item_appearance["id"].split("-")[-1])
                new_item = copy.copy(real_item)
                new_item.appearance = item_appearance
                item_map[body_id].append(new_item)

        for pet_appearance in all_pet_appearances:
            appearance = PetAppearance(
                state=self._state, size=size, data=pet_appearance["canonicalAppearance"]
            )

            neopet: Neopet = await Neopet._from_appearance(  # type: ignore
                appearance, items=item_map[appearance.body_id]
            )

            return_neopets.append(neopet)

        return return_neopets
