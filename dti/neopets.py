from os import PathLike
from typing import BinaryIO, List, Optional, Union

from .constants import GRAB_PET_APPEARANCES, PET_ON_NEOPETS, CLOSEST_POSES_IN_ORDER
from .enums import LayerImageSize, PetPose
from .errors import (
    InvalidColorSpeciesPair,
    MissingPetAppearance,
    NeopetNotFound,
    BrokenAssetImage,
)
from .models import Color, Item, PetAppearance, Species, AppearanceLayer
from .state import State


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
        name: Optional[str] = None,
    ):
        self.state = state
        self.species = species
        self.color = color
        self.appearances = appearances
        self.items = items or []
        self.name = name
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

        data = await state.http.query(
            query=GRAB_PET_APPEARANCES,
            variables={
                "allItemIds": item_ids or [],
                "speciesId": species.id,
                "colorId": color.id,
                "size": str(size or LayerImageSize.SIZE_600),
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
            PetAppearance(appearance) for appearance in data["petAppearances"]
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
                intersect_1 = set(item.appearance.restricted_zones).intersection(
                    {layer.zone for layer in temp.appearance.layers}
                )
                intersect_2 = set(temp.appearance.restricted_zones).intersection(
                    {layer.zone for layer in item.appearance.layers}
                )
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

        canvas = Image.new("RGBA", (600, 600))

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
            else:
                if foreground.mode == "1":  # bad
                    continue
                if foreground.mode != "RGBA":
                    foreground = foreground.convert("RGBA")
                canvas = Image.alpha_composite(canvas, foreground)

        canvas.save(fp, format="PNG")
        fp.seek(0)
