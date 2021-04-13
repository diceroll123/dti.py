import asyncio
from typing import Dict, List, Optional, Union, BinaryIO, Tuple
from urllib.parse import urlencode
from PIL import Image
from io import BytesIO

from .constants import (
    CLOSEST_POSES_IN_ORDER,
    GRAB_PET_APPEARANCES_BY_IDS,
    PET_ON_NEOPETS,
    GRAB_PET_APPEARANCES_BY_NAMES,
)
from .decorators import _require_state
from .enums import PetPose, LayerImageSize
from .errors import (
    MissingPetAppearance,
    InvalidColorSpeciesPair,
    NeopetNotFound,
    BrokenAssetImage,
)
from .mixins import Object
from .state import State, BitField


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

    __slots__ = ("_state", "id", "name")

    def __init__(self, *, state: State, data: Dict):
        self._state = state
        self.id = int(data["id"])
        self.name = data["name"]

    @_require_state
    async def _color_iterator(self, valid: bool = True) -> List["Color"]:
        found = []
        for color_id in range(1, self._state._valid_pairs.color_count + 1):
            is_valid = self._state._valid_pairs._check(
                species_id=self.id, color_id=color_id
            )
            if is_valid == valid:
                found.append(self._state._colors[color_id])
        return found

    async def colors(self) -> List["Color"]:
        """|coro|

        List[:class:`Color`]: Returns all colors this species can be painted.
        """
        return await self._color_iterator()

    async def missing_colors(self) -> List["Color"]:
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

    __slots__ = ("_state", "id", "name")

    def __init__(self, *, state: State, data: Dict):
        self._state = state
        self.id = int(data["id"])
        self.name = data["name"]

    @_require_state
    async def _species_iterator(self, valid: bool = True) -> List["Species"]:
        found = []
        for species_id in range(1, self._state._valid_pairs.species_count + 1):
            is_valid = self._state._valid_pairs._check(
                species_id=species_id, color_id=self.id
            )
            if is_valid == valid:
                found.append(self._state._species[species_id])
        return found

    async def species(self) -> List["Species"]:
        """|coro|

        List[:class:`Species`]: Returns all species this color can be painted on.
        """
        return await self._species_iterator()

    async def missing_species(self) -> List["Species"]:
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

    __slots__ = ("id", "depth", "label")

    def __init__(self, data: Dict):
        self.id = int(data["id"])
        self.depth = int(data["depth"])
        self.label = data["label"]

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
    id: :class:`str`
        The appearance layer's DTI ID. Guaranteed unique across all layers of all types.
    parent: Union[:class:`ItemAppearance`, :class:`PetAppearance`]
        The respective owner of this layer, an ItemAppearance or a PetAppearance.
    image_url: :class:`str`
        The appearance layer's DTI image url.
    asset_remote_id: :class:`str`
        The appearance layer's Neopets ID. Guaranteed unique across layers of the *same* type, but
        not of different types. That is, it's allowed and common for an item
        layer and a pet layer to have the same asset_remote_id.
    asset_type: :class:`str`
        The appearance layer's asset type. The only values this can have currently are `biology` and `object`,
        to differentiate between layers of a pet and layers of items respectively.
    zone: :class:`Zone`
        The appearance layer's zone.
    """

    __slots__ = ("id", "parent", "zone", "image_url", "asset_type", "asset_remote_id")

    def __init__(self, parent: Union["ItemAppearance", "PetAppearance"], **data):
        self.id = data["id"]
        self.parent = parent
        self.image_url = data["imageUrl"]
        self.asset_remote_id = data["remoteId"]
        self.zone = Zone(data["zone"])
        self.asset_type = data["asset_type"]

    def __repr__(self):
        return f"<AppearanceLayer zone={self.zone!r} url={self.image_url!r} parent={self.parent!r}>"


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
    id: :class:`str`
        The pet appearance's ID.
    body_id: :class:`str`
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
    """

    __slots__ = (
        "id",
        "body_id",
        "species",
        "color",
        "pose",
        "layers",
        "restricted_zones",
    )

    def __init__(self, *, state: State, data: Dict):
        self.id = data["id"]
        self.body_id = data["bodyId"]

        # create new, somewhat temporary colors from this data since we don't have async access
        self.color = Color(data=data["color"], state=state)
        self.species = Species(data=data["species"], state=state)

        self.pose = PetPose(data["pose"])
        self.layers = [
            AppearanceLayer(self, **layer, asset_type="biology")
            for layer in data["layers"]
        ]
        self.restricted_zones = [
            Zone(restricted) for restricted in data["restrictedZones"]
        ]

    def __repr__(self):
        return f"<PetAppearance species={self.species!r} color={self.color!r} pose={self.pose!r}>"


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
        The item appearance's ID.
    item: :class:`Item`
        The item that owns this appearance.
    layers: List[:class:`AppearanceLayer`]
        The appearance layers of the item appearance.
    restricted_zones: List[:class:`Zone`]
        The restricted zones of the item appearance. Outfits can't have conflicting restricted zones.
    occupies: List[:class:`Zone`]
        The zones that this item appearance occupies.
    """

    __slots__ = ("id", "item", "layers", "restricted_zones", "occupies")

    def __init__(self, data: Dict, item: "Item"):
        self.id = data["id"]
        self.item = item
        self.layers = [
            AppearanceLayer(self, **layer, asset_type="object")
            for layer in data["layers"]
        ]
        self.restricted_zones = [
            Zone(restricted) for restricted in data["restrictedZones"]
        ]
        self.occupies = [layer.zone for layer in self.layers]

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
    is_nc: :class:`bool`
        Whether or not the item is an NC-only item.
    is_pb: :class:`bool`
        Whether or not the item is a paintbrush color item, such as an Aisha's collar.
    rarity: :class:`int`
        The item's rarity on Neopets.
    appearance: Optional[:class:`ItemAppearance`]
        The item appearance object for this item on a particular PetAppearance. Can be `None`.
    waka_value: Optional[:class:`str`]
        The value of the item on waka's guide, according to wakaguide.com. Will be None is the value is unknown,
        or if there's an error getting the data.
    """

    __slots__ = (
        "id",
        "name",
        "description",
        "thumbnail_url",
        "appearance",
        "is_nc",
        "is_pb",
        "rarity",
        "waka_value",
    )

    def __init__(self, **data):
        self.id = int(data["id"])
        self.name = data.get("name")
        self.description = data.get("description")
        self.thumbnail_url = data.get("thumbnailUrl")
        self.is_nc = data.get("isNc")
        self.is_pb = data.get("isPb")
        self.rarity = int(data.get("rarityIndex"))
        self.waka_value = data.get("wakaValueText")

        appearance_data = data.get("appearanceOn", None)
        self.appearance = appearance_data and ItemAppearance(appearance_data, self)

    @property
    def is_np(self) -> bool:
        """:class:`bool`: Whether or not the item is an NP-only item."""
        return not self.is_nc and not self.is_pb

    @property
    def url(self) -> str:
        """:class:`str`: Returns the DTI URL for the item."""
        return (
            f'http://impress.openneo.net/items/{self.id}-{self.name.replace(" ", "-")}'
        )

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Item id={self.id} name={self.name!r} is_np={self.is_np} is_nc={self.is_nc} is_pb={self.is_pb} rarity={self.rarity}>"


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
    appearances: List[:class:`PetAppearance`]
        A list of the pet's appearances. This is essentially just a PetAppearance for each valid PetPose
    items: List[:class:`Item`]
        A list of the items that will be applied to the pet. Can be empty.
    size: Optional[:class:`LayerImageSize`]
        The desired size of the rendered image, or `None`.
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
        self.species = species
        self.color = color
        self.appearances = appearances
        self.items = items or []
        self.name = name
        self.size = size
        self.pose = pose
        self._valid_poses = valid_poses

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
    ) -> "Neopet":
        """Returns the data for a species+color+pose combo, optionally with items, an image size, and a name for internal usage."""

        if not await state._check(species_id=species.id, color_id=color.id):
            raise InvalidColorSpeciesPair(
                f"The {species} species does not have the color {color}"
            )

        size = size or LayerImageSize.SIZE_600

        variables = {
            "speciesId": species.id,
            "colorId": color.id,
            "size": str(size),
        }

        if item_names:
            variables["names"] = item_names or []
            query = GRAB_PET_APPEARANCES_BY_NAMES
            key = "itemsByName"
        else:
            variables["allItemIds"] = item_ids or []
            query = GRAB_PET_APPEARANCES_BY_IDS
            key = "items"

        data = await state._http._query(query=query, variables=variables)

        error = data.get("error")
        if error and "it is undefined" in error["message"]:
            raise InvalidColorSpeciesPair(
                f"The {species} species does not have the color {color}"
            )

        data = data["data"]
        items = [Item(**item) for item in data[key] if item is not None]
        appearances = [
            PetAppearance(data=appearance, state=state)
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
    ) -> "Neopet":
        """Returns the data for a specific neopet, by name."""

        size = size or LayerImageSize.SIZE_600

        data = await state._http._query(
            query=PET_ON_NEOPETS,
            variables={"petName": pet_name, "size": str(size)},
        )

        error = data.get("errors")
        if error:
            raise NeopetNotFound(error[0]["message"])

        data = data["data"]["petOnNeopetsDotCom"]

        pet_appearance = PetAppearance(data=data["petAppearance"], state=state)

        neopet = await Neopet._fetch_assets_for(
            species=pet_appearance.species,
            color=pet_appearance.color,
            pose=pet_appearance.pose,
            item_ids=[item["id"] for item in data["wornItems"]],
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
            objects, closet = self._render_items()
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
            objects, closet = self._render_items()
            params["objects[]"] = [item.id for item in objects]
            params["closet[]"] = [item.id for item in closet]

        return self._state._http.BASE + "/outfits/new?" + urlencode(params, doseq=True)

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

    def _render_items(self) -> Tuple[List[Item], List[Item]]:
        # Separates all items into what's wearable and what's in the closet.
        # Mimics DTI's method of getting rid of item conflicts in a FIFO manner.
        # Any conflicts go to the closet list.

        temp_items: List[Item] = []
        temp_closet: List[Item] = []
        for item in self.items:
            for temp in self.items:
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

    async def _render_layers(
        self, pose: Optional[PetPose] = None
    ) -> List[AppearanceLayer]:
        # Returns the image layers' images in order from bottom to top.
        # You may override the pose here.

        valid_poses = self.valid_poses(pose)

        if len(valid_poses) == 0:
            raise MissingPetAppearance(
                f'Pet Appearance <"{self.species.id}-{self.color.id}"> does not exist with any poses.'
            )

        pose = valid_poses[0]

        pet_appearance = self.get_pet_appearance(pose=pose)

        if pet_appearance is None:
            raise MissingPetAppearance(
                f'Pet Appearance <"{self.species.id}-{self.color.id}"> does not exist.'
            )

        all_layers = list(pet_appearance.layers)
        item_restricted_zones = []
        render_items, _ = self._render_items()
        for item in render_items:
            all_layers.extend(item.appearance.layers)

            item_restricted_zones.extend(item.appearance.restricted_zones)

        all_restricted_zones = set(
            item_restricted_zones + pet_appearance.restricted_zones
        )

        visible_layers = filter(
            lambda layer: layer.zone not in all_restricted_zones, all_layers
        )

        return sorted(visible_layers, key=lambda layer: layer.zone.depth)

    async def render(
        self,
        fp: BinaryIO,
        pose: Optional[PetPose] = None,
        size: Optional[LayerImageSize] = None,
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
        fp: BinaryIO
            A file-like object opened in binary mode and write mode (`wb`).
        pose: Optional[:class:`PetPose`]
            The desired pet pose for the render. Defaults to the current neopets' pose.
        size: Optional[:class:`LayerImageSize`]
            The desired size for the render. Defaults to the current neopets' pose if there is one,
            otherwise defaults to LayerImageSize.SIZE_600.

        Raises
        -------
        ~dti.BrokenAssetImage
            A layer's asset image is broken somehow on DTI's side.
        """

        pose = pose or self.pose

        sizes = {
            LayerImageSize.SIZE_150: 150,
            LayerImageSize.SIZE_300: 300,
            LayerImageSize.SIZE_600: 600,
        }

        img_size = sizes[size or self.size or LayerImageSize.SIZE_600]

        canvas = Image.new("RGBA", (img_size, img_size))

        layers = await self._render_layers(pose)

        # download images simultaneously
        images = await asyncio.gather(
            *[
                self._state._http._fetch_binary_data(_raise_if_none(layer))
                for layer in layers
            ]
        )

        for layer, image in zip(layers, images):
            try:
                layer_image = BytesIO(image)
                foreground = Image.open(layer_image)
            except Exception:
                # for when the image itself is corrupted somehow
                raise BrokenAssetImage(
                    f"Layer image broken: <Data species={self.species!r} color={self.color!r} pose={pose!r} layer={layer!r}>"
                )
            finally:
                if foreground.mode == "1":  # bad
                    continue
                if foreground.mode != "RGBA":
                    foreground = foreground.convert("RGBA")

                # force proper size if not already
                if foreground.size != (img_size, img_size):
                    foreground = foreground.resize((img_size, img_size))
                canvas = Image.alpha_composite(canvas, foreground)

        canvas.save(fp, format="PNG")
        fp.seek(0)


class Outfit(Object):
    """Represents a DTI Outfit.

    Attributes
    -----------
    id: :class:`int`
        The outfit's DTI ID.
    name: :class:`str`
        The outfit's name on DTI.
    pet_appearance: :class:`PetAppearance`
        The outfit's Neopets' pet appearance.
    worn_items: List[:class:`Item`]
        The items the Neopet is wearing.
    closeted_items: List[:class:`Item`]
        The items in the closet of the outfit.
    """

    __slots__ = (
        "_state",
        "id",
        "name",
        "pet_appearance",
        "worn_items",
        "closeted_items",
    )

    def __init__(self, *, state: State, **data):
        self._state = state
        self.id = data["id"]
        self.name = data["name"]
        self.pet_appearance = PetAppearance(data=data["petAppearance"], state=state)
        self.worn_items = [Item(**item_data) for item_data in data["wornItems"]]
        self.closeted_items = [Item(**item_data) for item_data in data["closetedItems"]]

    @property
    def url(self) -> str:
        """:class:`str`: Returns the outfit URL for the ID provided."""
        return f"https://impress.openneo.net/outfits/{self.id}"

    @property
    def image_urls(self):
        """:class:`Dict[str]`: Returns a dict of the different sizes for the rendered image url of an outfit for the ID provided."""
        new_id = str(self.id).zfill(9)
        id_folder = new_id[:3] + "/" + new_id[3:6] + "/" + new_id[6:]
        url = f"https://openneo-uploads.s3.amazonaws.com/outfits/{id_folder}/"

        return {
            "large": url + "preview.png",
            "medium": url + "medium_preview.png",
            "small": url + "small_preview.png",
        }

    async def render(
        self,
        fp: BinaryIO,
        pose: Optional[PetPose] = None,
        size: Optional[LayerImageSize] = None,
    ):
        pose = pose or self.pet_appearance.pose
        neopet = await Neopet._fetch_assets_for(
            species=self.pet_appearance.species,
            color=self.pet_appearance.color,
            pose=pose,
            size=size,
            item_ids=[item.id for item in self.worn_items],
            state=self._state,
        )
        await neopet.render(fp)

    render.__doc__ = Neopet.render.__doc__

    def __repr__(self):
        return f"<Outfit id={self.id} appearance={self.pet_appearance!r}>"


#  utility functions below
def _raise_if_none(layer: AppearanceLayer):
    url = layer.image_url
    if url is None:
        raise BrokenAssetImage(f"Layer image broken: {layer!r}")
    return url
