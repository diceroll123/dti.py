from typing import List, Literal, Optional, TypedDict, TypeVar, Union

PetPoseType = Literal[
    "HAPPY_MASC",
    "HAPPY_FEM",
    "SAD_MASC",
    "SAD_FEM",
    "SICK_MASC",
    "SICK_FEM",
    "UNCONVERTED",
    "UNKNOWN",
]


class _BaseObject(TypedDict):
    id: str


class SpeciesPayload(_BaseObject):
    name: str


class ColorPayload(_BaseObject):
    name: str


class ZonePayload(_BaseObject):
    depth: int
    label: str


class AppearanceLayerPayload(_BaseObject):
    imageUrl: Optional[str]
    bodyId: str
    remoteId: str
    zone: ZonePayload
    knownGlitches: List[str]


class PetAppearancePayload(_BaseObject):
    bodyId: str
    isGlitched: bool
    color: ColorPayload
    species: SpeciesPayload
    pose: PetPoseType
    layers: List[AppearanceLayerPayload]
    restrictedZones: List[ZonePayload]


class ItemAppearancePayload(_BaseObject):
    layers: List[AppearanceLayerPayload]
    restrictedZones: List[ZonePayload]


class BaseItemPayload(_BaseObject):
    name: str
    description: str
    thumbnailUrl: str
    isNc: bool
    isPb: bool
    rarityIndex: str


class ItemPayload(BaseItemPayload):
    appearanceOn: Optional[ItemAppearancePayload]


class UserPayload(_BaseObject):
    username: str


class OutfitPayload(_BaseObject):
    name: Optional[str]
    petAppearance: PetAppearancePayload
    wornItems: List[ItemPayload]
    closetedItems: List[ItemPayload]
    creator: Optional[UserPayload]
    createdAt: str
    updatedAt: str


# these are specific to the "fetch_neopet_by_name" http method.
class FetchedWornItemsPayload(_BaseObject):
    pass


class FetchedNeopetPayload(TypedDict):
    petAppearance: PetAppearancePayload
    wornItems: List[FetchedWornItemsPayload]


# specific to the "fetch_assets_for" http method
class FetchAssetsPayload(TypedDict):
    items: List[ItemPayload]
    petAppearance: PetAppearancePayload


# specific to the "fetch_all_appearances" http method
class ItemAllAppearancesPayload(BaseItemPayload):
    allAppearances: List[ItemAppearancePayload]


class CanonicalAppearancePayload(TypedDict):
    canonicalAppearance: PetAppearancePayload


class ColorAppliedToAllCompatibleSpeciesPayload(TypedDict):
    appliedToAllCompatibleSpecies: List[CanonicalAppearancePayload]


class FetchAllAppearancesPayload(TypedDict):
    items: List[ItemAllAppearancesPayload]
    color: ColorAppliedToAllCompatibleSpeciesPayload


ID = TypeVar("ID", bound=Union[str, int])
