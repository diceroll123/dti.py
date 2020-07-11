from os import PathLike
from typing import Dict, List, Optional, Union, BinaryIO

from .constants import CLOSEST_POSES_IN_ORDER, GRAB_PET_APPEARANCES, PET_ON_NEOPETS
from .decorators import _require_state
from .enums import PetPose, LayerImageSize
from .errors import (
    MissingPetAppearance,
    InvalidColorSpeciesPair,
    NeopetNotFound,
    BrokenAssetImage,
)
from .mixins import Object
from .state import State


class Species(Object):
    __slots__ = ("state", "id", "name")

    def __init__(self, state, data: Dict):
        self.state = state
        self.id = int(data["id"])
        self.name = data["name"]

    @_require_state
    async def _color_iterator(self, valid: bool = True) -> List["Color"]:
        found = []
        for color_id in range(1, self.state._valid_pairs.color_count + 1):
            is_valid = self.state._valid_pairs.check(
                species_id=self.id, color_id=color_id
            )
            if is_valid == valid:
                found.append(self.state._colors[color_id])
        return found

    async def colors(self) -> List["Color"]:
        return await self._color_iterator()

    async def missing_colors(self) -> List["Color"]:
        return await self._color_iterator(valid=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Species id={self.id} name={self.name!r}>"


class Color(Object):
    __slots__ = ("state", "id", "name")

    def __init__(self, state, data: Dict):
        self.state = state
        self.id = int(data["id"])
        self.name = data["name"]

    @_require_state
    async def _species_iterator(self, valid: bool = True) -> List["Species"]:
        found = []
        for species_id in range(1, self.state._valid_pairs.species_count + 1):
            is_valid = self.state._valid_pairs.check(
                species_id=species_id, color_id=self.id
            )
            if is_valid == valid:
                found.append(self.state._species[species_id])
        return found

    async def species(self) -> List["Species"]:
        return await self._species_iterator()

    async def missing_species(self) -> List["Species"]:
        return await self._species_iterator(valid=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Color id={self.id} name={self.name!r}>"


class Zone(Object):
    __slots__ = ("id", "depth", "label")

    def __init__(self, data: Dict):
        self.id = int(data["id"])
        self.depth = int(data["depth"])
        self.label = data["label"]

    def __repr__(self):
        return f"<Zone id={self.id} label={self.label!r} depth={self.depth}>"


class AppearanceLayer(Object):
    __slots__ = ("zone", "image_url", "asset_type", "asset_remote_id")

    def __init__(self, **data):
        self.image_url = data["imageUrl"]
        self.asset_remote_id = data["imageUrl"].split("/")[-1].split("_")[0]
        self.zone = Zone(data["zone"])
        self.asset_type = data["asset_type"]

    def __repr__(self):
        return f"<AppearanceLayer zone={self.zone!r} url={self.image_url!r} asset_type={self.asset_type!r}>"


class PetAppearance(Object):
    __slots__ = ("id", "body_id", "species", "color", "pet_state_id", "pose", "layers")

    def __init__(self, state, data: Dict):
        self.id = data["id"]  # formatted "SPECIES-COLOR-POSE"
        self.body_id = data["bodyId"]

        # create new, somewhat temporary colors from this data since we don't have async access
        self.color = Color(state, data["color"])
        self.species = Species(state, data["species"])

        self.pet_state_id = int(data["petStateId"])
        self.pose = PetPose(data["pose"])
        self.layers = [
            AppearanceLayer(**layer, asset_type="biology") for layer in data["layers"]
        ]


class ItemAppearance:
    __slots__ = ("layers", "restricted_zones")

    def __init__(self, data: Dict):
        self.layers = [
            AppearanceLayer(**layer, asset_type="object") for layer in data["layers"]
        ]
        self.restricted_zones = [
            Zone(restricted) for restricted in data["restrictedZones"]
        ]


class Item(Object):
    __slots__ = (
        "id",
        "name",
        "description",
        "thumbnail_url",
        "appearance",
        "is_nc",
        "rarity",
    )

    def __init__(self, **data):
        self.id = int(data["id"])
        self.name = data.get("name")
        self.description = data.get("description")
        self.thumbnail_url = data.get("thumbnailUrl")
        self.is_nc = data.get("isNc")
        self.rarity = data.get("rarityIndex")

        appearance_data = data.get("appearanceOn", None)
        self.appearance = appearance_data and ItemAppearance(appearance_data)

    @property
    def url(self) -> str:
        return (
            f'http://impress.openneo.net/items/{self.id}-{self.name.replace(" ", "-")}'
        )

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Item id={self.id} name={self.name!r} is_nc={self.is_nc} rarity={self.rarity}>"


class Neopet:
    __slots__ = (
        "_valid_poses",
        "state",
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
        state: State,
        *,
        species: Species,
        color: Color,
        valid_poses: int,
        pose: PetPose,
        appearances: List[PetAppearance],
        items: Optional[List[Item]] = None,
        size: Optional[LayerImageSize] = None,
        name: Optional[str] = None,
    ):
        self.state = state
        self.species = species
        self.color = color
        self.appearances = appearances
        self.items = items or []
        self.name = name
        self.size = size
        self.pose = pose
        self._valid_poses = valid_poses

    @classmethod
    async def fetch_assets_for(
        cls,
        state,
        *,
        species: Species,
        color: Color,
        pose: PetPose,
        item_ids: Optional[List[Union[str, int]]] = None,
        size: Optional[LayerImageSize] = None,
        name: Optional[str] = None,
    ) -> "Neopet":
        if not await state._check(species_id=species.id, color_id=color.id):
            raise InvalidColorSpeciesPair(
                f"The {species} species does not have the color {color}"
            )

        # note: sizes are not editable once the Neopet object is made
        size = size or LayerImageSize.SIZE_600

        data = await state.http.query(
            query=GRAB_PET_APPEARANCES,
            variables={
                "allItemIds": item_ids or [],
                "speciesId": species.id,
                "colorId": color.id,
                "size": str(size),
            },
        )

        error = data.get("error")
        if error:
            if "it is undefined" in error["message"]:
                raise InvalidColorSpeciesPair(
                    f"The {species} species does not have the color {color}"
                )

        data = data["data"]
        items = [Item(**item) for item in data["items"]]
        appearances = [
            PetAppearance(state, appearance) for appearance in data["petAppearances"]
        ]

        bit = await state._get_bit(species_id=species.id, color_id=color.id)

        return Neopet(
            state,
            species=species,
            color=color,
            pose=pose,
            valid_poses=bit,
            items=items,
            appearances=appearances,
            name=name,
            size=size,
        )

    @classmethod
    async def fetch_by_name(
        cls, state: State, pet_name: str, size: Optional[LayerImageSize] = None
    ) -> "Neopet":
        data = await state.http.query(
            query=PET_ON_NEOPETS, variables={"petName": pet_name}
        )

        error = data.get("errors")
        if error:
            raise NeopetNotFound(error[0]["message"])

        data = data["data"]["petOnNeopetsDotCom"]

        neopet = await Neopet.fetch_assets_for(
            state,
            species=await state._get_species(data["species"]["id"]),
            color=await state._get_color(data["color"]["id"]),
            item_ids=[item["id"] for item in data["items"]],
            pose=PetPose(data["pose"]),
            size=size,
            name=pet_name,
        )
        return neopet

    @property
    def legacy_closet_url(self) -> str:
        from urllib.parse import urlencode
        from collections import OrderedDict

        params = OrderedDict()
        if self.name:
            params["name"] = self.name

        params["species"] = self.species.id
        params["color"] = self.color.id

        valid_poses = self.valid_poses()
        if len(valid_poses):
            pet_state_id = self.get_pet_state_id(valid_poses[0])
            if pet_state_id:
                params["state"] = pet_state_id

        if self.items:
            params["objects[]"] = [item.id for item in self.items]
            params["closet[]"] = [item.id for item in self.items]

        return "https://impress.openneo.net/wardrobe#" + urlencode(params, doseq=True)

    @property
    def closet_url(self) -> str:
        from urllib.parse import urlencode
        from collections import OrderedDict

        params = OrderedDict()
        if self.name:
            params["name"] = self.name

        params["species"] = self.species.id
        params["color"] = self.color.id

        valid_poses = self.valid_poses()
        if len(valid_poses):
            params["pose"] = valid_poses[0]

        if self.items:
            params["objects[]"] = [item.id for item in self.items]

        return self.state.http.BASE + "/outfits/new?" + urlencode(params, doseq=True)

    def get_pet_appearance_id(self, pose: Optional[PetPose] = None) -> str:
        """Returns the provided pet appearance label"""
        pose = pose or self.pose
        return f"{self.species.id}-{self.color.id}-{pose.name}"

    def get_pet_state_id(self, pose: PetPose) -> Optional[int]:
        for appearance in self.appearances:
            if appearance.pose == pose:
                return appearance.pet_state_id
        return None

    def check(self, pose: PetPose) -> bool:
        return (self._valid_poses & pose) == pose

    def valid_poses(self, override_pose: Optional[PetPose] = None) -> List[PetPose]:
        pose = override_pose or self.pose
        return [p for p in CLOSEST_POSES_IN_ORDER[pose] if self.check(pose=p)]

    async def _render_layers(
        self, pose: Optional[PetPose] = None
    ) -> List[AppearanceLayer]:
        """Returns the image layers' images in order from bottom to top. You may override the pose."""

        valid_poses = self.valid_poses(pose)

        if len(valid_poses) == 0:
            raise MissingPetAppearance(
                f'Pet Appearance <"{self.species.id}-{self.color.id}"> does not exist with any poses.'
            )

        pose = valid_poses[0]

        pet_appearance = None
        find = self.get_pet_appearance_id(pose=pose)
        for appearance in self.appearances:
            if appearance.id == find:
                pet_appearance = appearance
                break

        if pet_appearance is None:
            raise MissingPetAppearance(f'Pet Appearance <"{find}"> does not exist.')

        layers = {}  # a key-value dict where keys are the depth

        # make a first-in-first-out for adding items, just to mimic DTI's way of getting rid of item conflicts
        temp_items: List[Item] = []
        for item in self.items:
            for temp in temp_items.copy():
                zones = {layer.zone for layer in temp.appearance.layers}
                intersect_1 = set(item.appearance.restricted_zones).intersection(zones)
                intersect_2 = set(temp.appearance.restricted_zones).intersection(zones)
                if intersect_1 or intersect_2:
                    temp_items.remove(temp)
            temp_items.append(item)

        restricted_zones = set()  # zone IDs of items going on the pet
        for item in temp_items:
            for restricted_zone in item.appearance.restricted_zones:
                restricted_zones.add(restricted_zone.id)

            for layer in item.appearance.layers:
                layers[layer.zone.depth] = layer

        for layer in pet_appearance.layers:
            if layer.zone.id in restricted_zones:
                # don't add something that is covered/etc by an item
                continue

            layers[layer.zone.depth] = layer

        return [layers[index] for index in sorted(layers.keys())]

    async def render(
        self,
        fp: Union[BinaryIO, PathLike],
        pose: Optional[PetPose] = None,
        fix_broken_assets: bool = False,
    ):
        """Outputs the rendered pet with the desired emotion + gender presentation to the file-like object passed.

        It is suggested to use something like BytesIO as the object, since this function can take a second or so since it downloads every layer.
        """
        pose = pose or self.pose

        from PIL import Image
        from io import BytesIO

        sizes = {
            LayerImageSize.SIZE_150: 150,
            LayerImageSize.SIZE_300: 300,
            LayerImageSize.SIZE_600: 600,
        }

        img_size = sizes[self.size or LayerImageSize.SIZE_600]

        canvas = Image.new("RGBA", (img_size, img_size))

        for layer in await self._render_layers(pose):
            layer_image = BytesIO(
                await self.state.http.get_binary_data(layer.image_url)
            )
            try:
                foreground = Image.open(layer_image)
            except Exception:
                raise_exception = True
                if fix_broken_assets:
                    attempt = await self.state.http.report_broken_asset(layer)
                    if attempt is not None:
                        raise_exception = False
                        foreground = Image.open(attempt)

                if raise_exception:
                    raise BrokenAssetImage(
                        f"Layer image broken: <Data species={self.species!r} color={self.color!r} layer={layer!r}>"
                    )
            finally:
                if foreground.mode == "1":  # bad
                    continue
                if foreground.mode != "RGBA":
                    foreground = foreground.convert("RGBA")
                canvas = Image.alpha_composite(canvas, foreground)

        canvas.save(fp, format="PNG")
        fp.seek(0)


class Outfit(Object):
    __slots__ = (
        "state",
        "id",
        "name",
        "pet_appearance",
        "worn_items",
        "closeted_items",
    )

    def __init__(self, state, **data):
        self.state = state
        self.id = data["id"]
        self.name = data["name"]
        self.pet_appearance = PetAppearance(state, data["petAppearance"])
        self.worn_items = [Item(**item_data) for item_data in data["wornItems"]]
        self.closeted_items = [Item(**item_data) for item_data in data["closetedItems"]]

    @property
    def url(self) -> str:
        return f"https://impress.openneo.net/outfits/{self.id}"

    async def render(
        self,
        fp: Union[BinaryIO, PathLike],
        pose: Optional[PetPose] = None,
        size: Optional[LayerImageSize] = None,
        fix_broken_assets: bool = False,
    ):
        pose = pose or self.pet_appearance.pose
        neopet = await Neopet.fetch_assets_for(
            self.state,
            species=self.pet_appearance.species,
            color=self.pet_appearance.color,
            pose=pose,
            size=size,
            item_ids=[item.id for item in self.worn_items],
        )
        await neopet.render(fp, fix_broken_assets=fix_broken_assets)
