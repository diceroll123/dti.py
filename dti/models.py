from typing import Dict, List

from .decorators import _require_state
from .enums import PetPose
from .mixins import Object


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
    __slots__ = ("id", "pet_state_id", "pose", "layers")

    def __init__(self, data: Dict):
        self.id = data["id"]  # formatted "SPECIES-COLOR-POSE"
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

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Item id={self.id} name={self.name!r}>"
