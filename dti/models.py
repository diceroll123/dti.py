from __future__ import annotations

import asyncio
import datetime
import io
import os
from typing import TYPE_CHECKING, Any, Sequence, overload
from urllib.parse import urlencode

from dti.types import FetchAssetsPayload, FetchedNeopetPayload

from . import utils
from .enums import (
    AppearanceLayerKnownGlitch,
    AppearanceLayerType,
    ItemKind,
    LayerImageSize,
    PetPose,
    try_enum,
)
from .errors import InvalidColorSpeciesPair, MissingPetAppearance, NullAssetImage
from .mixins import Object

if TYPE_CHECKING:
    from .state import BitField, State
    from .types import (
        ID,
        AppearanceLayerPayload,
        ColorPayload,
        ItemAppearancePayload,
        ItemPayload,
        OutfitPayload,
        PetAppearancePayload,
        SpeciesPayload,
        ZonePayload,
    )

__all__: tuple[str, ...] = (
    "Species",
    "Color",
    "Zone",
    "AppearanceLayer",
    "PetAppearance",
    "ItemAppearance",
    "Item",
    "User",
    "Neopet",
    "Outfit",
)


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

    __slots__: tuple[str, ...] = (
        "_state",
        "id",
        "name",
    )

    if TYPE_CHECKING:
        id: int

    def __init__(self, *, state: State, data: SpeciesPayload) -> None:
        self._state = state
        self.id = int(data["id"])
        self.name: str = data["name"]

    async def _color_iterator(self, valid: bool = True) -> list[Color]:
        await self._state._lock_and_update()  # type: ignore

        found: list[Color] = []
        for color_id, color in self._state._colors.items():  # type: ignore
            is_valid = self._state._valid_pairs._check(  # type: ignore
                species_id=self.id, color_id=int(color_id)
            )
            if is_valid == valid:
                found.append(color)
        return found

    async def colors(self) -> list[Color]:
        """|coro|

        List[:class:`Color`]: Returns all colors this species can be painted.
        """
        return await self._color_iterator()

    async def missing_colors(self) -> list[Color]:
        """|coro|

        List[:class:`Color`]: Returns all colors this species can not be painted.
        """
        return await self._color_iterator(valid=False)

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.id

    def __repr__(self) -> str:
        return f"<Species id={self.id} name={self.name!r}>"


class Color(Object):
    """Represents a Neopets color.

    .. container:: operations

        .. describe:: x == y

            Checks if two colors are equal.

        .. describe:: x != y

            Checks if two colors are not equal.

        .. describe:: hash(x)

            Returns the color's hash.

        .. describe:: str(x)

            Returns the color's name.

    Attributes
    -----------
    name: :class:`str`
        The color name.
    id: :class:`int`
        The color ID.
    """

    __slots__: tuple[str, ...] = (
        "_state",
        "id",
        "name",
    )

    def __init__(self, *, state: State, data: ColorPayload) -> None:
        self._state = state
        self.id: int = int(data["id"])
        self.name: str = data["name"]

    async def _species_iterator(self, valid: bool = True) -> list[Species]:
        await self._state._lock_and_update()  # type: ignore

        found: list[Species] = []
        for species_id, species in self._state._species.items():  # type: ignore
            is_valid = self._state._valid_pairs._check(  # type: ignore
                species_id=int(species_id), color_id=self.id
            )
            if is_valid == valid:
                found.append(species)
        return found

    async def species(self) -> list[Species]:
        """|coro|

        List[:class:`Species`]: Returns all species this color can be painted on.
        """
        return await self._species_iterator()

    async def missing_species(self) -> list[Species]:
        """|coro|

        List[:class:`Species`]: Returns all species this color can not be painted on.
        """
        return await self._species_iterator(valid=False)

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.id

    def __repr__(self) -> str:
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

    __slots__: tuple[str, ...] = (
        "id",
        "depth",
        "label",
    )

    def __init__(self, data: ZonePayload) -> None:
        self.id: int = int(data["id"])
        self.depth: int = data["depth"]
        self.label: str = data["label"]

    def __repr__(self) -> str:
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
    asset_remote_id: :class:`int`
        The appearance layer's Neopets ID. Guaranteed unique across layers of the *same* type, but
        not of different types. That is, it's allowed and common for an item
        layer and a pet layer to have the same asset_remote_id.
    asset_type: :class:`AppearanceLayerType`
        The appearance layer's asset type.
    body_id: :class:`int`
        The appearance layer's body ID.
    zone: :class:`Zone`
        The appearance layer's zone.
    known_glitches: Optional[List[:class:`AppearanceLayerKnownGlitch`]]
        Known glitches for this appearance layer. Returns None if the list is empty.
    """

    __slots__: tuple[str, ...] = (
        "_state",
        "id",
        "parent",
        "zone",
        "_image_url",
        "asset_type",
        "asset_remote_id",
        "known_glitches",
        "body_id",
    )

    def __init__(
        self,
        *,
        parent: ItemAppearance | PetAppearance,
        data: AppearanceLayerPayload,
    ) -> None:
        self._state: State = parent._state  # type: ignore
        self.id: int = int(data["id"])
        self.parent: ItemAppearance | PetAppearance = parent
        self._image_url: str | None = data["imageUrl"]
        self.asset_remote_id: int = int(data["remoteId"])
        self.body_id: int = int(data["bodyId"])
        self.zone: Zone = Zone(data["zone"])
        self.known_glitches: list[AppearanceLayerKnownGlitch] | None = [
            try_enum(AppearanceLayerKnownGlitch, glitch)
            for glitch in data["knownGlitches"]
        ] or None

        self.asset_type = (
            AppearanceLayerType.BIOLOGY
            if isinstance(parent, PetAppearance)
            else AppearanceLayerType.OBJECT
        )

    @property
    def image_url(self) -> str | None:
        """Optional[:class:`str`]: The appearance layer's PNG image url. If this is None, the item has a complex movie-based image.
        Rendering these will raise an error.
        """

        if self._image_url is None:
            return None

        return utils.url_sanitizer(self._image_url)

    async def read(self) -> bytes:
        """|coro|

        Retrieves the content of this asset as a :class:`bytes` object.

        Raises
        ------
        ~dti.NullAssetImage
            The image URL for this asset was returned by DTI as a null object.

        Returns
        -------
        :class:`bytes`
            The content of the asset.
        """
        if self.image_url is None:
            raise NullAssetImage(f"Layer image missing: {self!r}")
        return await self._state.http._fetch_binary_data(self.image_url)  # type: ignore

    def __repr__(self) -> str:
        attrs: list[tuple[str, Any]] = [
            ("id", self.id),
            ("asset_remote_id", self.asset_remote_id),
            ("zone", self.zone),
            ("url", self.image_url),
            ("parent", self.parent),
            ("asset_type", self.asset_type),
        ]
        joined = " ".join("%s=%r" % t for t in attrs)
        return f"<AppearanceLayer {joined}>"


class PetAppearance(Object):
    """Represents the render-able state of a Neopet.

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
        Whether or not this appearance is marked as glitched. Not to be confused with the layers having their own
        glitches, for that, check out :attr:`PetAppearance.has_glitches`.
    """

    __slots__: tuple[str, ...] = (
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
    ) -> None:
        self._state = state
        self.id: int = int(data["id"])
        self.body_id: int = int(data["bodyId"])
        self.is_glitched: bool = data["isGlitched"]
        self.size = size

        # create new, somewhat temporary colors from this data since we don't have async access
        self.color: Color = Color(data=data["color"], state=state)
        self.species: Species = Species(data=data["species"], state=state)

        self.pose: PetPose = PetPose(data["pose"])
        self.layers: list[AppearanceLayer] = [
            AppearanceLayer(parent=self, data=layer) for layer in data["layers"]
        ]
        self.restricted_zones: list[Zone] = [
            Zone(restricted) for restricted in data["restrictedZones"]
        ]

    @property
    def has_glitches(self) -> bool:
        """:class:`bool`: Whether or not any of the layers in this appearance are marked as glitched."""
        return any(layer.known_glitches is not None for layer in self.layers)

    @property
    def url(self) -> str:
        """:class:`str`: The URL of this pet appearance as an editable outfit."""
        return f"https://impress-2020.openneo.net/outfits/new?species={self.species.id}&color={self.color.id}&pose={self.pose.name}&state={self.id}"

    def __repr__(self) -> str:
        attrs: list[tuple[str, Any]] = [
            ("id", self.id),
            ("species", self.species),
            ("color", self.color),
            ("pose", self.pose),
            ("is_glitched", self.is_glitched),
        ]
        joined = " ".join("%s=%r" % t for t in attrs)
        return f"<PetAppearance {joined}>"

    def _render_layers(
        self, items: Sequence[Item] | None = None
    ) -> list[AppearanceLayer]:
        # Returns the image layers' images in order from bottom to top.

        all_layers: list[AppearanceLayer] = list(self.layers)
        item_restricted_zones: list[Zone] = []
        pet_occupied_and_restricted_zones: set[Zone] = {
            layer.zone for layer in all_layers
        } | set(self.restricted_zones)

        if items:
            render_items, _ = _render_items(items)
            for item in render_items:
                if item.appearance is None:
                    continue

                all_layers.extend(item.appearance.layers)

                item_restricted_zones.extend(item.appearance.restricted_zones)

        def _layer_filter(layer: AppearanceLayer) -> bool:
            ##############################################
            #            NOTES STOLEN FROM DTI           #
            ##############################################

            #  When an item restricts a zone, it hides pet layers of the same zone.
            #  We use this to e.g. make a hat hide a hair ruff.
            #
            #  NOTE: Items' restricted layers also affect what items you can wear at
            #        the same time. We don't enforce anything about that here, and
            #        instead assume that the input by this point is valid!
            if (
                layer.asset_type == AppearanceLayerType.BIOLOGY
                and layer.zone in item_restricted_zones
            ):
                return False

            # When a pet appearance restricts or occupies a zone, or when the pet is
            # Unconverted, it makes body-specific items incompatible. We use this to
            # disallow UCs from wearing certain body-specific Biology Effects,
            # Statics, etc, while still allowing non-body-specific items in those
            # zones! (I think this happens for some Invisible pet stuff, too?)
            if (
                layer.asset_type == AppearanceLayerType.OBJECT
                and layer.body_id != 0
                and (
                    self.pose == PetPose.UNCONVERTED
                    or layer.zone in pet_occupied_and_restricted_zones
                )
            ):
                return False

            # A pet appearance can also restrict its own zones. The Wraith Uni is an
            # interesting example: it has a horn, but its zone restrictions hide it!
            if (
                layer.asset_type == AppearanceLayerType.BIOLOGY
                and layer.zone in self.restricted_zones
            ):
                return False

            return True

        visible_layers = filter(_layer_filter, all_layers)

        return sorted(visible_layers, key=lambda layer: layer.zone.depth)

    def image_url(self, *, items: Sequence[Item] | None = None) -> str:
        """
        Parameters
        -----------
        items: Optional[Sequence[:class:`Item`]]
            An optional list of items to render on this appearance.

        Raises
        -------
        ~dti.NullAssetImage
            The species does not exist.

        Returns
        --------
        :class:`str`
            The DTI server-side-rendering image url of a Neopet appearance.
        """

        layers: list[AppearanceLayer] = self._render_layers(items)
        layer_urls: list[str] = []

        try:
            for layer in layers:
                if img := layer.image_url:
                    layer_urls.append(img)
                    continue
                raise TypeError
        except TypeError as e:
            missing: list[AppearanceLayer] = [
                layer for layer in layers if layer.image_url is None
            ]
            raise NullAssetImage(
                f"Null image URLs found in this render: {missing}"
            ) from e
        return utils.build_layers_url(layer_urls, size=self.size)

    async def read(self, *, items: Sequence[Item] | None = None) -> bytes:
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
        return await self._state.http._fetch_binary_data(self.image_url(items=items))  # type: ignore

    async def render(
        self,
        fp: str | bytes | os.PathLike[Any] | io.BufferedIOBase,
        /,
        *,
        items: Sequence[Item] | None = None,
        seek_begin: bool = True,
    ) -> None:
        """|coro|

        Outputs the rendered pet with the desired emotion + gender presentation to the file-like object passed.

        It is suggested to use something like BytesIO as the object, since this function can take a second or
        so since it downloads every layer, and you'd be keeping a file object open on the disk
        for an indeterminate amount of time.

        .. note::

            Only supports PNG output.

        Parameters
        -----------
        fp: Union[:class:`str`, :class:`bytes`, :class:`io.BufferedIOBase`, :class:`os.PathLike`]
            A path string, or a file-like object opened in binary mode and write mode (`wb`).
        items: Optional[Sequence[:class:`Item`]]
            An optional list of items to render on this appearance.
        seek_begin: :class:`bool`
            Whether to seek to the beginning of the file after saving is successfully done.
        """

        data: bytes = await self.read(items=items)

        def write() -> None:
            if isinstance(fp, io.BufferedIOBase):
                fp.write(data)
                if seek_begin:
                    fp.seek(0)
            else:
                with open(fp, "wb") as f:
                    f.write(data)

        await asyncio.get_running_loop().run_in_executor(None, write)


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

    __slots__: tuple[str, ...] = (
        "_state",
        "id",
        "item",
        "layers",
        "restricted_zones",
        "occupies",
    )

    def __init__(self, data: ItemAppearancePayload, item: Item) -> None:
        self._state: State = item._state  # type: ignore
        self.id: str = data["id"]
        self.item: Item = item
        self.layers: list[AppearanceLayer] = [
            AppearanceLayer(parent=self, data=layer) for layer in data["layers"]
        ]
        self.restricted_zones: list[Zone] = [
            Zone(restricted) for restricted in data["restrictedZones"]
        ]
        self.occupies: list[Zone] = [layer.zone for layer in self.layers]

    def __repr__(self) -> str:
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
    """

    __slots__: tuple[str, ...] = (
        "_state",
        "_appearance",
        "id",
        "name",
        "kind",
        "description",
        "thumbnail_url",
        "rarity",
    )

    def __init__(self, *, data: ItemPayload, state: State) -> None:
        self._state = state
        self.id: int = int(data["id"])
        self.name: str = data["name"]
        self.description: str = data["description"]
        self.thumbnail_url: str = utils.url_sanitizer(data["thumbnailUrl"])
        self._appearance: ItemAppearance | None = None
        self.appearance = data.get("appearanceOn")

        _kind = None
        if data.get("isNc"):
            _kind = ItemKind.NC
        if data.get("isPb"):
            _kind = ItemKind.PB
        self.kind: ItemKind = _kind or ItemKind.NP

        self.rarity: int = int(data["rarityIndex"])

    @property
    def appearance(self) -> ItemAppearance | None:
        """The item appearance object for this item on a particular PetAppearance. Can be `None`."""
        return self._appearance

    @appearance.setter
    def appearance(self, val: ItemAppearancePayload | ItemAppearance | None) -> None:
        if val is not None:
            if isinstance(val, ItemAppearance):
                self._appearance = val
            else:
                # assume it's a ItemAppearancePayload
                self._appearance = ItemAppearance(val, self)
        else:
            self._appearance = None

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

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<Item id={self.id} name={self.name!r} kind={self.kind} rarity={self.rarity}>"


class User(Object):
    """Represents a Dress To Impress user.

    Attributes
    -----------
    id: :class:`int`
        The user's ID.
    username: :class:`str`
        The user's username.
    """

    __slots__: tuple[str, ...] = (
        "id",
        "username",
    )

    def __init__(self, **data: str) -> None:
        self.id: int = int(data["id"])
        self.username: str = data["username"]

    def __str__(self) -> str:
        return self.username

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


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
    appearance: :class:`PetAppearance`
        The appearance of this pet's species + color + pose + size.
    items: List[:class:`Item`]
        A list of the items that will be applied to the pet. Can be empty.
    name: Optional[:class:`str`]
        The name of the Neopet, if one is supplied.
    """

    __slots__: tuple[str, ...] = (
        "_valid_poses",
        "_state",
        "species",
        "color",
        "appearance",
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
        appearance: PetAppearance,
        items: Sequence[Item] | None = None,
        size: LayerImageSize | None = None,
        name: str | None = None,
        state: State,
    ):
        self._state: State = state
        self.species: Species = species
        self.color: Color = color
        self.appearance: PetAppearance = appearance
        self.items: Sequence[Item] = items or []
        self.name: str | None = name
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
        item_ids: Sequence[ID] | None = None,
        item_names: Sequence[str] | None = None,
        size: LayerImageSize | None = None,
        name: str | None = None,
        state: State,
    ) -> Neopet:
        """Returns the data for a species+color+pose combo, optionally with items, an image size, and a name for internal usage."""

        if not await state._check(species_id=species.id, color_id=color.id):  # type: ignore
            raise InvalidColorSpeciesPair(
                f"According to DTI, the {species} species does not have the color {color}. If it's newly released, it must be modeled first!"
            )

        size = size or LayerImageSize.SIZE_600

        data: FetchAssetsPayload = await state.http.fetch_assets_for(
            species=species,
            color=color,
            pose=pose,
            item_ids=item_ids,
            item_names=item_names,
            size=size,
        )

        items: list[Item] = [
            Item(data=item, state=state) for item in data["items"] if item is not None
        ]

        appearance = PetAppearance(data=data["petAppearance"], size=size, state=state)

        bit: BitField = await state._get_bit(species_id=species.id, color_id=color.id)  # type: ignore

        return Neopet(
            species=species,
            color=color,
            pose=pose,
            valid_poses=bit,
            items=items,
            appearance=appearance,
            name=name,
            size=size,
            state=state,
        )

    @overload
    @classmethod
    async def _from_appearance(
        cls,
        pet_appearance: PetAppearance,
        /,
        *,
        item: Item | None = None,
    ) -> Neopet:
        ...

    @overload
    @classmethod
    async def _from_appearance(
        cls,
        pet_appearance: PetAppearance,
        /,
        *,
        items: Sequence[Item] | None = None,
    ) -> Neopet:
        ...

    @classmethod
    async def _from_appearance(
        cls,
        pet_appearance: PetAppearance,
        /,
        *,
        item: Item | None = None,
        items: Sequence[Item] | None = None,
    ) -> Neopet:
        """Makes a single-use Neopet object, as opposed to Neopet.from_appearance, which is a more full object with all appearance data etc. This is for internal use only."""

        species: Species = pet_appearance.species
        color: Color = pet_appearance.color
        state: State = pet_appearance._state  # type: ignore

        _items: list[Item] = []

        if item:
            _items.append(item)

        if items:
            _items.extend(items)

        bit = await state._get_bit(species_id=species.id, color_id=color.id)  # type: ignore

        return cls(
            species=species,
            color=color,
            pose=pet_appearance.pose,
            valid_poses=bit,
            items=_items,
            appearance=pet_appearance,
            size=pet_appearance.size,
            state=state,
        )

    @classmethod
    async def _fetch_by_name(
        cls, *, state: State, pet_name: str, size: LayerImageSize
    ) -> Neopet:
        """Returns the data for a specific neopet, by name."""

        size = size or LayerImageSize.SIZE_600

        pet_on_neo: FetchedNeopetPayload = await state.http.fetch_neopet_by_name(
            name=pet_name, size=size
        )

        pet_appearance = PetAppearance(
            data=pet_on_neo["petAppearance"], size=size, state=state
        )

        neopet: Neopet = await Neopet._fetch_assets_for(
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

        params: dict[str, Any] = {
            "name": self.name or "",
            "species": self.species.id,
            "color": self.color.id,
            "state": self.appearance.id,
        }

        if self.items:
            objects, closet = _render_items(self.items)
            params["objects[]"] = [item.id for item in objects]
            params["closet[]"] = [item.id for item in closet]

        return "https://impress.openneo.net/wardrobe#" + urlencode(params, doseq=True)

    @property
    def closet_url(self) -> str:
        """:class:`str`: Returns the closet URL for a Neopet customization."""

        params: dict[str, Any] = {
            "name": self.name or "",
            "species": self.species.id,
            "color": self.color.id,
            "pose": str(self.pose),
        }

        if self.items:
            objects, closet = _render_items(self.items)
            params["objects[]"] = [item.id for item in objects]
            params["closet[]"] = [item.id for item in closet]

        return "https://impress-2020.openneo.net/outfits/new?" + urlencode(
            params, doseq=True
        )

    def clear_closet(self) -> None:
        """Removes items from the closet that would not be rendered to the pet appearance."""
        _, closet = _render_items(self.items)
        new_items: list[Item] = [item for item in self.items if item not in closet]
        self.items = new_items

    @property
    def is_glitched(self) -> bool:
        """:class:`bool`: Returns whether or not the render of this pet has any known glitches."""
        if self.appearance.is_glitched:
            return True

        if self.appearance.has_glitches:
            return True

        items, _ = _render_items(self.items)
        for item in items:
            if item.appearance:
                for layer in item.appearance.layers:
                    if layer.known_glitches:
                        return True

        return False

    def check(self, pose: PetPose) -> bool:
        """:class:`bool`: Returns True if the pet pose provided is valid for the current species+color."""
        return self._valid_poses.check(pose)

    async def render(
        self,
        fp: str | bytes | os.PathLike[Any] | io.BufferedIOBase,
        /,
        *,
        pose: PetPose | None = None,
        seek_begin: bool = True,
    ) -> None:
        """|coro|

        Outputs the rendered pet with the desired emotion + gender presentation to the file-like object passed.

        It is suggested to use something like BytesIO as the object, since this function can take a second or
        so since it downloads every layer, and you'd be keeping a file object open on the disk
        for an indeterminate amount of time.

        .. note::

            Only supports PNG output.

        Parameters
        -----------
        fp: Union[:class:`str`, :class:`bytes`, :class:`io.BufferedIOBase`, :class:`os.PathLike`]
            A path string, or a file-like object opened in binary mode and write mode (`wb`).
        pose: Optional[:class:`PetPose`]
            The desired pet pose for the render. Defaults to the current neopets' pose.
        seek_begin: :class:`bool`
            Whether to seek to the beginning of the file after saving is successfully done.

        Raises
        -------
        ~dti.BrokenAssetImage
            A layer's asset image is broken somehow on DTI's side.
        """

        pet_appearance = self.appearance

        if pose is not None and pose != self.pose:
            # override pose here
            is_valid: bool = self.check(pose)
            if not is_valid:
                raise MissingPetAppearance(
                    f'Pet Appearance <"{self.species.id}-{self.color.id}-{pose.name}"> does not exist.'
                )

            data: PetAppearancePayload = await self._state.http.fetch_appearance(
                species=self.species, color=self.color, pose=pose, size=self.size
            )
            pet_appearance = PetAppearance(data=data, size=self.size, state=self._state)

        await pet_appearance.render(fp, items=self.items, seek_begin=seek_begin)

    @staticmethod
    async def from_outfit(
        outfit: Outfit, /, *, size: LayerImageSize | None = None
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
            state=outfit._state,  # type: ignore
        )

    @staticmethod
    async def from_appearance(
        appearance: PetAppearance, /, *, size: LayerImageSize | None = None
    ) -> Neopet:
        """|coro|

        Converts a PetAppearance object into a Neopet object, which is a little more flexible.

        Parameters
        -----------
        appearance: :class:`PetAppearance`
            The PetAppearance you'd like to convert to a Neopet object.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the image. If one is not supplied, it defaults to the outfit's size.
        """

        return await Neopet._fetch_assets_for(
            species=appearance.species,
            color=appearance.color,
            pose=appearance.pose,
            size=size or appearance.size,
            state=appearance._state,  # type: ignore
        )

    @property
    def image_url(self) -> str:
        """:class:`str`: Convenience property for getting a Neopet's pet appearance render url."""
        return self.appearance.image_url(items=self.items)

    def __repr__(self):
        attrs = [
            ("species", self.species),
            ("color", self.color),
            ("pose", self.pose),
            ("size", self.size),
            ("appearance", self.appearance),
            ("items", [item.id for item in self.items] or None),
        ]
        if self.name:
            # let's put the name in front if there is one.
            attrs.insert(0, ("name", self.name))  # type: ignore
        joined = " ".join("%s=%r" % t for t in attrs)
        return f"<Neopet {joined}>"


class Outfit(Object):
    """Represents a DTI Outfit.

    Attributes
    -----------
    id: :class:`int`
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

    __slots__: tuple[str, ...] = (
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
        self.id = int(data["id"])
        self.name: str | None = data["name"]
        self.size = size
        self.pet_appearance: PetAppearance = PetAppearance(
            data=data["petAppearance"], size=size, state=state
        )
        self.worn_items: list[Item] = [
            Item(data=item_data, state=state) for item_data in data["wornItems"]
        ]
        self.closeted_items: list[Item] = [
            Item(data=item_data, state=state) for item_data in data["closetedItems"]
        ]
        self.creator: User | None = User(**data["creator"]) if data["creator"] else None

        # in an effort to cut down on dependencies, at a small performance cost,
        # we will simply truncate the trailing "Z" from the timestamps
        # for more info see https://discuss.python.org/t/parse-z-timezone-suffix-in-datetime/2220
        self.created_at: datetime.datetime = datetime.datetime.fromisoformat(
            data["createdAt"][:-1]
        ).replace(tzinfo=datetime.timezone.utc)
        self.updated_at: datetime.datetime = datetime.datetime.fromisoformat(
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

    def image_url(self, *, size: LayerImageSize | None = None) -> str:
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

        updated_at = int(self.updated_at.timestamp())
        size_str = str(size or self.size)[-3:]
        return f"https://outfits.openneo-assets.net/outfits/{self.id}/v/{updated_at}/{size_str}.png"

    async def read(self, *, size: LayerImageSize | None = None) -> bytes:
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
        return await self._state.http._fetch_binary_data(self.image_url(size=size))  # type: ignore

    async def render(
        self,
        fp: str | bytes | os.PathLike[Any] | io.BufferedIOBase,
        /,
        *,
        pose: PetPose | None = None,
        size: LayerImageSize | None = None,
        seek_begin: bool = True,
    ) -> None:
        """|coro|

        Outputs the rendered pet with the desired emotion + gender presentation to the file-like object passed.

        It is suggested to use something like BytesIO as the object, since this function can take a second or
        so since it downloads every layer, and you'd be keeping a file object open on the disk
        for an indeterminate amount of time.

        .. note::

            Only supports PNG output.

        Parameters
        -----------
        fp: Union[:class:`str`, :class:`bytes`, :class:`io.BufferedIOBase`, :class:`os.PathLike`]
            A path string, or a file-like object opened in binary mode and write mode (`wb`).
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
            neopet: Neopet = await Neopet.from_outfit(self, size=size or self.size)
            await neopet.render(fp, pose=pose, seek_begin=seek_begin)
        else:
            # render from outfit ID
            data: bytes = await self.read(size=size or self.size)

            def write() -> None:
                if isinstance(fp, io.BufferedIOBase):
                    fp.write(data)
                    if seek_begin:
                        fp.seek(0)
                else:
                    with open(fp, "wb") as f:
                        f.write(data)

            await asyncio.get_running_loop().run_in_executor(None, write)

    def __repr__(self) -> str:
        attrs: list[tuple[str, Any]] = [
            ("id", self.id),
            ("appearance", self.pet_appearance),
            ("created_at", self.created_at),
            ("updated_at", self.updated_at),
        ]
        joined = " ".join("%s=%r" % t for t in attrs)
        return f"<Outfit {joined}>"


#  utility functions below


def _render_items(items: Sequence[Item]) -> tuple[list[Item], list[Item]]:
    # Separates all items into what's wearable and what's in the closet.
    # Mimics DTI's method of getting rid of item conflicts in a FIFO manner.
    # Any conflicts go to the closet list.

    temp_items: list[Item] = []
    temp_closet: list[Item] = []
    for item in items:
        for temp in items:
            if item == temp:
                continue

            if temp not in temp_items:
                continue

            if item.appearance is None or temp.appearance is None:
                continue

            intersect_1: set[Zone] = set(item.appearance.occupies).intersection(
                temp.appearance.occupies + temp.appearance.restricted_zones
            )
            intersect_2: set[Zone] = set(temp.appearance.occupies).intersection(
                item.appearance.occupies + item.appearance.restricted_zones
            )

            if intersect_1 or intersect_2:
                temp_closet.append(temp)
                temp_items.remove(temp)
        temp_items.append(item)

    return temp_items, temp_closet
