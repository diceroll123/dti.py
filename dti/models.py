from __future__ import annotations

import datetime
import io
import logging
import os
import urllib.parse
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple, Union
from urllib.parse import urlencode

from .constants import (
    CLOSEST_POSES_IN_ORDER,
    GRAB_PET_APPEARANCES_WITH_ITEMS_BY_IDS,
    GRAB_PET_APPEARANCES_WITH_ITEMS_BY_NAMES,
    PET_ON_NEOPETS,
)
from .decorators import _require_state
from .enums import (
    AppearanceLayerKnownGlitch,
    AppearanceLayerType,
    ItemKind,
    LayerImageSize,
    PetPose,
    try_enum,
)
from .errors import (
    InvalidColorSpeciesPair,
    MissingPetAppearance,
    NeopetNotFound,
    NullAssetImage,
)
from .mixins import Object
from .state import BitField, State

if TYPE_CHECKING:
    from .types import (
        AppearanceLayerPayload,
        ColorPayload,
        ItemAppearancePayload,
        ItemPayload,
        OutfitPayload,
        PetAppearancePayload,
        SpeciesPayload,
        ZonePayload,
    )

log = logging.getLogger(__name__)


class Species(Object):
    """Represents a Neopets species.

    .. container:: operations

        .. describe:: x == y

            Checks if two species are equal.

        .. describe:: x != y

            Checks if two species are not equal.

        .. describe:: hash(x)

            Returns the species' hash.

        .. describe:: str(x)

            Returns the species' name.

    Attributes
    -----------
    name: :class:`str`
        The species name.
    id: :class:`int`
        The species ID.
    """

    __slots__ = (
        "_state",
        "id",
        "name",
    )

    def __init__(self, *, state: State, data: SpeciesPayload):
        self._state = state
        self.id = int(data["id"])
        self.name: str = data["name"]

    @_require_state
    async def _color_iterator(self, valid: bool = True) -> List[Color]:
        found = []
        for color_id in range(1, self._state._valid_pairs.color_count + 1):
            is_valid = self._state._valid_pairs._check(
                species_id=self.id, color_id=color_id
            )
            if is_valid == valid:
                found.append(self._state._colors[color_id])
        return found

    async def colors(self) -> List[Color]:
        """|coro|

        List[:class:`Color`]: Returns all colors this species can be painted.
        """
        return await self._color_iterator()

    async def missing_colors(self) -> List[Color]:
        """|coro|

        List[:class:`Color`]: Returns all colors this species can not be painted.
        """
        return await self._color_iterator(valid=False)

    def __str__(self):
        return self.name

    def __int__(self):
        return self.id

    def __repr__(self):
        return f"<Species id={self.id} name={self.name!r}>"


class Color(Object):
    """Represents a Neopets color.

    .. container:: operations

        .. describe:: x == y

            Checks if two colors are equal.

        .. describe:: x != y

            Checks if two colors are not equal.

        .. describe:: hash(x)

            Returns the color' hash.

        .. describe:: str(x)

            Returns the color' name.

    Attributes
    -----------
    name: :class:`str`
        The color name.
    id: :class:`int`
        The color ID.
    """

    __slots__ = (
        "_state",
        "id",
        "name",
    )

    def __init__(self, *, state: State, data: ColorPayload):
        self._state = state
        self.id: int = int(data["id"])
        self.name: str = data["name"]

    @_require_state
    async def _species_iterator(self, valid: bool = True) -> List[Species]:
        found = []
        for species_id in range(1, self._state._valid_pairs.species_count + 1):
            is_valid = self._state._valid_pairs._check(
                species_id=species_id, color_id=self.id
            )
            if is_valid == valid:
                found.append(self._state._species[species_id])
        return found

    async def species(self) -> List[Species]:
        """|coro|

        List[:class:`Species`]: Returns all species this color can be painted on.
        """
        return await self._species_iterator()

    async def missing_species(self) -> List[Species]:
        """|coro|

        List[:class:`Species`]: Returns all species this color can not be painted on.
        """
        return await self._species_iterator(valid=False)

    def __str__(self):
        return self.name

    def __int__(self):
        return self.id

    def __repr__(self):
        return f"<Color id={self.id} name={self.name!r}>"


class Zone(Object):
    """Represents a wearable zone.

    .. container:: operations

        .. describe:: x == y

            Checks if two zones are equal.

        .. describe:: x != y

            Checks if two zones are not equal.

        .. describe:: hash(x)

            Returns the zone's hash.

    Attributes
    -----------
    label: :class:`str`
        The zone label.
    id: :class:`int`
        The zone ID.
    depth: :class:`int`
        The zone depth.
    """

    __slots__ = (
        "id",
        "depth",
        "label",
    )

    def __init__(self, data: ZonePayload):
        self.id: int = int(data["id"])
        self.depth: int = data["depth"]
        self.label: str = data["label"]

    def __repr__(self):
        return f"<Zone id={self.id} label={self.label!r} depth={self.depth}>"


class AppearanceLayer(Object):
    """Represents a wearable appearance layer. Literally, it is one of the image layers of a rendered customization.

    .. container:: operations

        .. describe:: x == y

            Checks if two appearance layers are equal.

        .. describe:: x != y

            Checks if two appearance layers are not equal.

        .. describe:: hash(x)

            Returns the appearance layer's hash.

    Attributes
    -----------
    id: :class:`int`
        The appearance layer's DTI ID. Guaranteed unique across all layers of all types.
    parent: Union[:class:`ItemAppearance`, :class:`PetAppearance`]
        The respective owner of this layer, an ItemAppearance or a PetAppearance.
    image_url: Optional[:class:`str`]
        The appearance layer's PNG image url. If this is None, the item has a complex movie-based image.
        Rendering these will raise an error.
    asset_remote_id: :class:`int`
        The appearance layer's Neopets ID. Guaranteed unique across layers of the *same* type, but
        not of different types. That is, it's allowed and common for an item
        layer and a pet layer to have the same asset_remote_id.
    asset_type: :class:`AppearanceLayerType`
        The appearance layer's asset type.
    zone: :class:`Zone`
        The appearance layer's zone.
    known_glitches: Optional[List[:class:`AppearanceLayerKnownGlitch`]]
        Known glitches for this appearance layer. Returns None if the list is empty.
    """

    __slots__ = (
        "_state",
        "id",
        "parent",
        "zone",
        "image_url",
        "asset_type",
        "asset_remote_id",
        "known_glitches",
    )

    def __init__(
        self,
        *,
        parent: Union[ItemAppearance, PetAppearance],
        data: AppearanceLayerPayload,
    ):
        self._state = parent._state
        self.id: int = int(data["id"])
        self.parent: Union[ItemAppearance, PetAppearance] = parent
        self.image_url: Optional[str] = data["imageUrl"]
        self.asset_remote_id: int = int(data["remoteId"])
        self.zone: Zone = Zone(data["zone"])
        self.known_glitches: Optional[List[AppearanceLayerKnownGlitch]] = [
            try_enum(AppearanceLayerKnownGlitch, glitch)
            for glitch in data["knownGlitches"]
        ] or None

        self.asset_type = (
            AppearanceLayerType.BIOLOGY
            if isinstance(parent, PetAppearance)
            else AppearanceLayerType.OBJECT
        )

    async def read(self) -> bytes:
        """|coro|

        Retrieves the content of this asset as a :class:`bytes` object.

        Raises
        ------
        BrokenAssetImage
            The image URL for this asset was returned by DTI as a null object.

        Returns
        -------
        :class:`bytes`
            The content of the asset.
        """
        if self.image_url is None:
            raise NullAssetImage(f"Layer image missing: {self!r}")
        return await self._state._http._fetch_binary_data(self.image_url)

    def __repr__(self):
        attrs = [
            ("id", self.id),
            ("asset_remote_id", self.asset_remote_id),
            ("zone", self.zone),
            ("url", self.image_url),
            ("parent", self.parent),
        ]
        joined = " ".join("%s=%r" % t for t in attrs)
        return f"<AppearanceLayer {joined}>"


class PetAppearance(Object):
    """Represents the renderable state of a Neopet.

    .. container:: operations

        .. describe:: x == y

            Checks if two pet appearances are equal.

        .. describe:: x != y

            Checks if two pet appearances are not equal.

        .. describe:: hash(x)

            Returns the pet appearance's hash.

    Attributes
    -----------
    id: :class:`int`
        The pet appearance's ID.
    body_id: :class:`int`
        The pet appearance's body ID.
    color: :class:`Color`
        The color of the pet appearance.
    species: :class:`Species`
        The species of the pet appearance.
    pose: :class:`PetPose`
        The pose of the pet appearance.
    layers: List[:class:`AppearanceLayer`]
        The appearance layers of the pet appearance.
    restricted_zones: List[:class:`Zone`]
        The restricted zones of the pet appearance. Outfits can't have conflicting restricted zones.
    is_glitched: :class:`bool`
        Whether or not this appearance is marked as glitched.
    """

    __slots__ = (
        "_state",
        "id",
        "body_id",
        "species",
        "color",
        "pose",
        "layers",
        "restricted_zones",
        "is_glitched",
        "size",
    )

    def __init__(
        self, *, state: State, size: LayerImageSize, data: PetAppearancePayload
    ):
        self._state = state
        self.id: int = int(data["id"])
        self.body_id: int = int(data["bodyId"])
        self.is_glitched: bool = data["isGlitched"]
        self.size = size

        # create new, somewhat temporary colors from this data since we don't have async access
        self.color: Color = Color(data=data["color"], state=state)
        self.species: Species = Species(data=data["species"], state=state)

        self.pose: PetPose = PetPose(data["pose"])
        self.layers: List[AppearanceLayer] = [
            AppearanceLayer(parent=self, data=layer) for layer in data["layers"]
        ]
        self.restricted_zones: List[Zone] = [
            Zone(restricted) for restricted in data["restrictedZones"]
        ]

    @property
    def url(self) -> str:
        return f"https://impress-2020.openneo.net/outfits/new?species={self.species.id}&color={self.color.id}&pose={self.pose.name}&state={self.id}"

    def __repr__(self):
        attrs = [
            ("id", self.id),
            ("species", self.species),
            ("color", self.color),
            ("pose", self.pose),
            ("is_glitched", self.is_glitched),
        ]
        joined = " ".join("%s=%r" % t for t in attrs)
        return f"<PetAppearance {joined}>"

    def _render_layers(self, items: Optional[Sequence[Item]]) -> List[AppearanceLayer]:
        # Returns the image layers' images in order from bottom to top.

        all_layers = list(self.layers)
        item_restricted_zones = []
        if items:
            render_items, _ = _render_items(items)
            for item in render_items:
                all_layers.extend(item.appearance.layers)

                item_restricted_zones.extend(item.appearance.restricted_zones)

        all_restricted_zones = set(item_restricted_zones + self.restricted_zones)

        visible_layers = filter(
            lambda layer: layer.zone not in all_restricted_zones, all_layers
        )

        return sorted(visible_layers, key=lambda layer: layer.zone.depth)

    def image_url(self, items: Optional[Sequence[Item]] = None) -> str:
        """
        Parameters
        -----------
        items: Optional[Sequence[:class:`Item`]]
            An optional list of items to render on this appearance.

        Returns
        --------
        :class:`str`
            The DTI server-side-rendering image url of a Neopet appearance.
        """

        size_px = int(str(self.size)[-3:])

        layers = self._render_layers(items)

        try:
            layer_urls = ",".join(layer.image_url for layer in layers)
        except TypeError:
            # expected str, NoneType found
            missing = [layer for layer in layers if layer.image_url is None]
            raise NullAssetImage(f"Null image URLs found in this render: {missing}")

        return f"https://impress-2020.openneo.net/api/outfitImage?size={size_px}&layerUrls={layer_urls}"

    async def read(self, items: Optional[Sequence[Item]] = None) -> bytes:
        """|coro|

        Retrieves the content of the server-side-rendered image of this pet appearance as a :class:`bytes` object.

        Parameters
        -----------
        items: Optional[Sequence[:class:`Item`]]
            An optional list of items to render on this appearance.

        Returns
        -------
        :class:`bytes`
            The content of the rendered image.
        """
        return await self._state._http._fetch_binary_data(self.image_url(items=items))

    async def render(
        self,
        fp: Union[str, bytes, os.PathLike, io.BufferedIOBase],
        *,
        items: Optional[Sequence[Item]] = None,
        seek_begin: bool = True,
    ):
        """|coro|

        Outputs the rendered pet with the desired emotion + gender presentation to the file-like object passed.

        It is suggested to use something like BytesIO as the object, since this function can take a second or
        so since it downloads every layer, and you'd be keeping a file object open on the disk
        for an indeterminate amount of time.

        .. note::

            Only supports PNG output.

        Parameters
        -----------
        fp: Union[:class:`io.BufferedIOBase`, :class:`os.PathLike`]
            A file-like object opened in binary mode and write mode (`wb`).
        items: Optional[Sequence[:class:`Item`]]
            An optional list of items to render on this appearance.
        seek_begin: :class:`bool`
            Whether to seek to the beginning of the file after saving is successfully done.
        """

        fp.write(await self.read(items=items))

        if seek_begin and isinstance(fp, io.BufferedIOBase):
            fp.seek(0)


class ItemAppearance(Object):
    """Represents the renderable state of an item.

    .. container:: operations

        .. describe:: x == y

            Checks if two item appearances are equal.

        .. describe:: x != y

            Checks if two item appearances are not equal.

        .. describe:: hash(x)

            Returns the item appearance's hash.

    Attributes
    -----------
    id: :class:`str`
        The item appearance's ID. A string that looks something like "item-#####-body-##"
    item: :class:`Item`
        The item that owns this appearance.
    layers: List[:class:`AppearanceLayer`]
        The appearance layers of the item appearance.
    restricted_zones: List[:class:`Zone`]
        The restricted zones of the item appearance. Outfits can't have conflicting restricted zones.
    occupies: List[:class:`Zone`]
        The zones that this item appearance occupies.
    """

    __slots__ = (
        "_state",
        "id",
        "item",
        "layers",
        "restricted_zones",
        "occupies",
    )

    def __init__(self, data: ItemAppearancePayload, item: Item):
        self._state = item._state
        self.id: str = data["id"]
        self.item: Item = item
        self.layers: List[AppearanceLayer] = [
            AppearanceLayer(parent=self, data=layer) for layer in data["layers"]
        ]
        self.restricted_zones: List[Zone] = [
            Zone(restricted) for restricted in data["restrictedZones"]
        ]
        self.occupies: List[Zone] = [layer.zone for layer in self.layers]

    def __repr__(self):
        return f"<ItemAppearance id={self.id!r} item={self.item!r}>"


class Item(Object):
    """Represents a Neopets item.

    .. container:: operations

        .. describe:: x == y

            Checks if two items are equal.

        .. describe:: x != y

            Checks if two items are not equal.

        .. describe:: hash(x)

            Returns the item's hash.

        .. describe:: str(x)

            Returns the item's name.

    Attributes
    -----------
    id: :class:`int`
        The item's Neopets ID.
    name: :class:`str`
        The item's name.
    description: :class:`str`
        The description of the item.
    thumbnail_url: :class:`str`
        The item image URL.
    kind: :class:`ItemKind`
        The kind of item this is. Can be `NC` for Neocash, `NP` for Neopoint items, or `PB` for paintbrush items.
    rarity: :class:`int`
        The item's rarity on Neopets.
    appearance: Optional[:class:`ItemAppearance`]
        The item appearance object for this item on a particular PetAppearance. Can be `None`.
    waka_value: Optional[:class:`str`]
        The value of the item on waka's guide, according to wakaguide.com. Will be None is the value is unknown,
        or if there's an error getting the data.
    """

    __slots__ = (
        "_state",
        "id",
        "name",
        "kind",
        "description",
        "thumbnail_url",
        "appearance",
        "rarity",
        "waka_value",
    )

    def __init__(self, *, data: ItemPayload, state: State):
        self._state = state
        self.id: int = int(data["id"])
        self.name: str = data.get("name")
        self.description: str = data.get("description")
        self.thumbnail_url: str = data.get("thumbnailUrl")

        _kind = None
        if data.get("isNc"):
            _kind = ItemKind.NC
        if data.get("isPb"):
            _kind = ItemKind.PB
        self.kind = _kind or ItemKind.NP

        self.rarity: int = int(data.get("rarityIndex"))
        self.waka_value: Optional[str] = data.get("wakaValueText")

        appearance_data = data.get("appearanceOn", None)
        self.appearance: Optional[ItemAppearance] = appearance_data and ItemAppearance(
            appearance_data, self
        )

    @property
    def legacy_url(self) -> str:
        """:class:`str`: Returns the legacy DTI URL for the item."""
        return (
            f'http://impress.openneo.net/items/{self.id}-{self.name.replace(" ", "-")}'
        )

    @property
    def url(self) -> str:
        """:class:`str`: Returns the DTI URL for the item."""
        return f"https://impress-2020.openneo.net/items/{self.id}"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Item id={self.id} name={self.name!r} is_np={self.is_np} is_nc={self.is_nc} is_pb={self.is_pb} rarity={self.rarity}>"


class User(Object):
    """Represents a Dress To Impress user.

    Attributes
    -----------
    id: :class:`int`
        The user's ID.
    username: :class:`str`
        The user's username.
    """

    __slots__ = (
        "id",
        "username",
    )

    def __init__(self, **data):
        self.id: int = int(data["id"])
        self.username: str = data["username"]

    def __str__(self):
        return self.username

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


class Neopet:
    """Represents a customizable Neopet.

    Attributes
    -----------
    species: :class:`Species`
        The Neopets' species.
    color: :class:`Color`
        The Neopets' color.
    pose: :class:`PetPose`
        The Neopets' pose.
    size: :class:`LayerImageSize`
        The size of the rendered image.
    appearances: List[:class:`PetAppearance`]
        A list of the pet's appearances. This is essentially just a PetAppearance for each valid PetPose
    items: List[:class:`Item`]
        A list of the items that will be applied to the pet. Can be empty.
    name: Optional[:class:`str`]
        The name of the Neopet, if one is supplied.
    """

    __slots__ = (
        "_valid_poses",
        "_state",
        "species",
        "color",
        "appearances",
        "items",
        "name",
        "pose",
        "size",
    )

    def __init__(
        self,
        *,
        species: Species,
        color: Color,
        valid_poses: BitField,
        pose: PetPose,
        appearances: List[PetAppearance],
        items: Optional[List[Item]] = None,
        size: Optional[LayerImageSize] = None,
        name: Optional[str] = None,
        state: State,
    ):
        self._state = state
        self.species: Species = species
        self.color: Color = color
        self.appearances: List[PetAppearance] = appearances
        self.items: List[Item] = items or []
        self.name: Optional[str] = name
        self.size: LayerImageSize = size or LayerImageSize.SIZE_600
        self.pose: PetPose = pose
        self._valid_poses: BitField = valid_poses

    @classmethod
    async def _fetch_assets_for(
        cls,
        *,
        species: Species,
        color: Color,
        pose: PetPose,
        item_ids: Optional[List[Union[str, int]]] = None,
        item_names: Optional[List[str]] = None,
        size: Optional[LayerImageSize] = None,
        name: Optional[str] = None,
        state: State,
    ) -> Neopet:
        """Returns the data for a species+color+pose combo, optionally with items, an image size, and a name for internal usage."""

        if not await state._check(species_id=species.id, color_id=color.id):
            raise InvalidColorSpeciesPair(
                f"According to DTI, the {species} species does not have the color {color}. If it's newly released, it must be modeled first!"
            )

        size = size or LayerImageSize.SIZE_600

        variables = {
            "speciesId": species.id,
            "colorId": color.id,
            "size": str(size),
        }

        if item_names:
            variables["names"] = item_names or []
            query = GRAB_PET_APPEARANCES_WITH_ITEMS_BY_NAMES
            key = "itemsByName"
        else:
            variables["allItemIds"] = item_ids or []
            query = GRAB_PET_APPEARANCES_WITH_ITEMS_BY_IDS
            key = "items"

        data = await state._http._query(query=query, variables=variables)

        if data is None:
            # an error we were not prepared for has occurred, let's find it!
            log.critical(
                f"Somehow, the API returned null for a query. Params: {variables!r}"
            )
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data."
            )

        error = data.get("error", None)
        if error:
            if "it is undefined" in error["message"]:
                raise InvalidColorSpeciesPair(
                    f"According to DTI, the {species} species does not have the color {color}. If it's newly released, it must be modeled first!"
                )

            log.critical("Unhandled error occurred in data: " + str(data))
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data."
            )

        if "data" not in data:
            # an error we were not prepared for has occurred, let's find it!
            log.critical("Unknown pet appearance data returned: " + str(data))
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data."
            )

        data = data["data"]
        items = [Item(data=item, state=state) for item in data[key] if item is not None]
        appearances = [
            PetAppearance(data=appearance, size=size, state=state)
            for appearance in data["petAppearances"]
        ]

        bit = await state._get_bit(species_id=species.id, color_id=color.id)

        return Neopet(
            species=species,
            color=color,
            pose=pose,
            valid_poses=bit,
            items=items,
            appearances=appearances,
            name=name,
            size=size,
            state=state,
        )

    @classmethod
    async def _fetch_by_name(
        cls, *, state: State, pet_name: str, size: Optional[LayerImageSize] = None
    ) -> Neopet:
        """Returns the data for a specific neopet, by name."""

        size = size or LayerImageSize.SIZE_600

        data = await state._http._query(
            query=PET_ON_NEOPETS,
            variables={"petName": pet_name, "size": str(size)},
        )

        # the API responds with an error AND with [data][petOnNeopetsDotCom] being null,
        # so let's just check the latter first
        if "data" not in data:
            # an error we were not prepared for has occurred, let's find it!
            log.critical("Unknown pet appearance data returned: " + str(data))
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data."
            )

        pet_on_neo = data["data"]["petOnNeopetsDotCom"]
        if pet_on_neo is None:
            raise NeopetNotFound("This pet does not seem to exist.")

        error = data.get("errors")
        if error:
            log.critical("Unhandled error occurred in data: " + str(data))
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data."
            )

        pet_appearance = PetAppearance(
            data=pet_on_neo["petAppearance"], size=size, state=state
        )

        neopet = await Neopet._fetch_assets_for(
            species=pet_appearance.species,
            color=pet_appearance.color,
            pose=pet_appearance.pose,
            item_ids=[item["id"] for item in pet_on_neo["wornItems"]],
            size=size,
            name=pet_name,
            state=state,
        )
        return neopet

    @property
    def legacy_closet_url(self) -> str:
        """:class:`str`: Returns the legacy closet URL for a Neopet customization."""

        params = {
            "name": self.name or "",
            "species": self.species.id,
            "color": self.color.id,
        }

        valid_poses = self.valid_poses()
        if len(valid_poses):
            appearance = self.get_pet_appearance(valid_poses[0])
            if appearance:
                params["state"] = appearance.id

        if self.items:
            objects, closet = _render_items(self.items)
            params["objects[]"] = [item.id for item in objects]
            params["closet[]"] = [item.id for item in closet]

        return "https://impress.openneo.net/wardrobe#" + urlencode(params, doseq=True)

    @property
    def closet_url(self) -> str:
        """:class:`str`: Returns the closet URL for a Neopet customization."""

        params = {
            "name": self.name or "",
            "species": self.species.id,
            "color": self.color.id,
        }

        valid_poses = self.valid_poses()
        if len(valid_poses):
            params["pose"] = valid_poses[0]

        if self.items:
            objects, closet = _render_items(self.items)
            params["objects[]"] = [item.id for item in objects]
            params["closet[]"] = [item.id for item in closet]

        return "https://impress-2020.openneo.net/outfits/new?" + urlencode(
            params, doseq=True
        )

    def get_pet_appearance(self, pose: PetPose) -> Optional[PetAppearance]:
        """Optional[:class:`PetAppearance`]: Returns the pet appearance for the provided pet pose."""
        for appearance in self.appearances:
            if appearance.pose == pose:
                return appearance
        return None

    def check(self, pose: PetPose) -> bool:
        """:class:`bool`: Returns True if the pet pose provided is valid for the current species+color."""
        return self._valid_poses.check(pose)

    def valid_poses(self, override_pose: Optional[PetPose] = None) -> List[PetPose]:
        """List[:class:`PetPose`]: Returns a list of valid pet poses for the current species+color."""
        pose = override_pose or self.pose
        return [p for p in CLOSEST_POSES_IN_ORDER[pose] if self.check(pose=p)]

    async def render(
        self,
        fp: Union[str, bytes, os.PathLike, io.BufferedIOBase],
        pose: Optional[PetPose] = None,
        pet_appearance: Optional[PetAppearance] = None,
        *,
        seek_begin: bool = True,
    ):
        """|coro|

        Outputs the rendered pet with the desired emotion + gender presentation to the file-like object passed.

        It is suggested to use something like BytesIO as the object, since this function can take a second or
        so since it downloads every layer, and you'd be keeping a file object open on the disk
        for an indeterminate amount of time.

        .. note::

            Only supports PNG output.

        Parameters
        -----------
        fp: Union[:class:`io.BufferedIOBase`, :class:`os.PathLike`]
            A file-like object opened in binary mode and write mode (`wb`).
        pose: Optional[:class:`PetPose`]
            The desired pet pose for the render. Defaults to the current neopets' pose.
        pet_appearance: Optional[:class:`PetAppearance`]
            The desired pet appearance for the render. This overrides any pose passed in.
        seek_begin: :class:`bool`
            Whether to seek to the beginning of the file after saving is successfully done.

        Raises
        -------
        ~dti.BrokenAssetImage
            A layer's asset image is broken somehow on DTI's side.
        """

        if pet_appearance is None:
            # You may override the pose here, if no appearance is passed in.
            pose = pose or self.pose

            valid_poses = self.valid_poses(pose)

            if len(valid_poses) == 0:
                raise MissingPetAppearance(
                    f'Pet Appearance <"{self.species.id}-{self.color.id}-{pose.name}"> does not exist with any poses.'
                )

            pose = valid_poses[0]

            pet_appearance = self.get_pet_appearance(pose=pose)

        if pet_appearance is None:
            raise MissingPetAppearance(
                f'Pet Appearance <"{self.species.id}-{self.color.id}"> does not exist.'
            )

        await pet_appearance.render(fp, items=self.items, seek_begin=seek_begin)

    @staticmethod
    async def from_outfit(
        outfit: Outfit, size: Optional[LayerImageSize] = None
    ) -> Neopet:
        """|coro|

        Converts an Outfit object into a Neopet object, which is a little more flexible.

        Parameters
        -----------
        outfit: :class:`Outfit`
            The Outfit you'd like to convert to a Neopet object.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the image. If one is not supplied, it defaults to the outfit's size.
        """

        return await Neopet._fetch_assets_for(
            species=outfit.pet_appearance.species,
            color=outfit.pet_appearance.color,
            pose=outfit.pet_appearance.pose,
            size=size or outfit.size,
            item_ids=[item.id for item in outfit.worn_items],
            state=outfit._state,
        )


class Outfit(Object):
    """Represents a DTI Outfit.

    Attributes
    -----------
    id: :class:`str`
        The outfit's DTI ID.
    name: Optional[:class:`str`]
        The outfit's name on DTI. Can be None.
    size: :class:`LayerImageSize`
        The size of the rendered image.
    creator: Optional[:class:`User`]
        The outfit's creator. Can be None if the outfit was made anonymously.
    pet_appearance: :class:`PetAppearance`
        The outfit's Neopets' pet appearance.
    worn_items: List[:class:`Item`]
        The items the Neopet is wearing. Can be empty.
    closeted_items: List[:class:`Item`]
        The items in the closet of the outfit. Can be empty.
    created_at: :class:`datetime.datetime`
        The outfit's creation time in UTC.
    updated_at: :class:`datetime.datetime`
        The outfit's last updated time in UTC.
    """

    __slots__ = (
        "_state",
        "id",
        "name",
        "creator",
        "pet_appearance",
        "worn_items",
        "closeted_items",
        "created_at",
        "updated_at",
        "size",
    )

    def __init__(self, *, state: State, size: LayerImageSize, data: OutfitPayload):
        self._state = state
        self.id = data["id"]
        self.name: Optional[str] = data["name"]
        self.size = size
        self.pet_appearance: PetAppearance = PetAppearance(
            data=data["petAppearance"], size=size, state=state
        )
        self.worn_items: List[Item] = [
            Item(data=item_data, state=state) for item_data in data["wornItems"]
        ]
        self.closeted_items: List[Item] = [
            Item(data=item_data, state=state) for item_data in data["closetedItems"]
        ]
        self.creator: Optional[User] = (
            User(**data["creator"]) if data["creator"] else None
        )

        # in an effort to cut down on dependencies, at a small performance cost,
        # we will simply truncate the trailing "Z" from the timestamps
        # for more info see https://discuss.python.org/t/parse-z-timezone-suffix-in-datetime/2220
        self.created_at = datetime.datetime.fromisoformat(
            data["createdAt"][:-1]
        ).replace(tzinfo=datetime.timezone.utc)
        self.updated_at = datetime.datetime.fromisoformat(
            data["updatedAt"][:-1]
        ).replace(tzinfo=datetime.timezone.utc)

    @property
    def legacy_url(self) -> str:
        """:class:`str`: Returns the legacy outfit URL for the ID provided."""
        return f"https://impress.openneo.net/outfits/{self.id}"

    @property
    def url(self) -> str:
        """:class:`str`: Returns the outfit URL for the ID provided."""
        return f"https://impress-2020.openneo.net/outfits/{self.id}"

    def image_url(self, size: Optional[LayerImageSize] = None) -> str:
        """
        Parameters
        -----------
        size: Optional[:class:`LayerImageSize`]
            The desired size for the image. If one is not supplied, it defaults to the outfit's size.

        Returns
        --------
        :class:`str`
            The image url of an outfit.
        """

        params = {
            "id": self.id,
            "size": str(size or self.size)[-3:],
            "updatedAt": int(self.updated_at.timestamp()),
        }

        encoded = urllib.parse.urlencode(params)
        return f"https://impress-2020.openneo.net/api/outfitImage?{encoded}"

    async def read(self, size: Optional[LayerImageSize] = None) -> bytes:
        """|coro|

        Retrieves the content of the server-side-rendered image of this outfit as a :class:`bytes` object.

        Parameters
        -----------
        size: Optional[LayerImageSize]
            The desired size for the image. If one is not supplied, it defaults to the outfit's size.

        Returns
        -------
        :class:`bytes`
            The content of the rendered image.
        """
        return await self._state._http._fetch_binary_data(self.image_url(size=size))

    async def render(
        self,
        fp: Union[str, bytes, os.PathLike, io.BufferedIOBase],
        pose: Optional[PetPose] = None,
        size: Optional[LayerImageSize] = None,
        *,
        seek_begin: bool = True,
    ):
        """|coro|

        Outputs the rendered pet with the desired emotion + gender presentation to the file-like object passed.

        It is suggested to use something like BytesIO as the object, since this function can take a second or
        so since it downloads every layer, and you'd be keeping a file object open on the disk
        for an indeterminate amount of time.

        .. note::

            Only supports PNG output.

        Parameters
        -----------
        fp: Union[:class:`io.BufferedIOBase`, :class:`os.PathLike`]
            A file-like object opened in binary mode and write mode (`wb`).
        pose: Optional[:class:`PetPose`]
            The desired pet pose for the render. Defaults to the outfit's pose.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the render. Defaults to the outfit's pose.
        seek_begin: :class:`bool`
            Whether to seek to the beginning of the file after saving is successfully done.

        Raises
        -------
        ~dti.BrokenAssetImage
            A layer's asset image is broken somehow on DTI's side.
        """

        # if there's a pose or size change, we have to rebuild as a Neopet render
        rebuild = False

        if pose and pose != self.pet_appearance.pose:
            rebuild = True

        if size and size != self.size:
            rebuild = True

        if rebuild:
            neopet = await Neopet.from_outfit(self, size or self.size)
            await neopet.render(fp, pose=pose, seek_begin=seek_begin)
        else:
            # render from outfit ID
            fp.write(await self.read(size=size or self.size))

            if seek_begin and isinstance(fp, io.BufferedIOBase):
                fp.seek(0)

    def __repr__(self):
        attrs = [
            ("id", self.id),
            ("appearance", self.pet_appearance),
            ("created_at", self.created_at),
            ("updated_at", self.updated_at),
        ]
        joined = " ".join("%s=%r" % t for t in attrs)
        return f"<Outfit {joined}>"


#  utility functions below


def _render_items(items: Sequence[Item]) -> Tuple[List[Item], List[Item]]:
    # Separates all items into what's wearable and what's in the closet.
    # Mimics DTI's method of getting rid of item conflicts in a FIFO manner.
    # Any conflicts go to the closet list.

    temp_items: List[Item] = []
    temp_closet: List[Item] = []
    for item in items:
        for temp in items:
            if item == temp:
                continue

            if temp not in temp_items:
                continue

            intersect_1 = set(item.appearance.occupies).intersection(
                temp.appearance.occupies + temp.appearance.restricted_zones
            )
            intersect_2 = set(temp.appearance.occupies).intersection(
                item.appearance.occupies + item.appearance.restricted_zones
            )

            if intersect_1 or intersect_2:
                temp_closet.append(temp)
                temp_items.remove(temp)
        temp_items.append(item)

    return temp_items, temp_closet
