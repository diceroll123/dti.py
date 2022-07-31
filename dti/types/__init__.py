from __future__ import annotations

from typing import Literal, TypedDict, TypeVar, Union

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
    imageUrl: str | None
    bodyId: str
    remoteId: str
    zone: ZonePayload
    knownGlitches: list[str]


class PetAppearancePayload(_BaseObject):
    bodyId: str
    isGlitched: bool
    color: ColorPayload
    species: SpeciesPayload
    pose: PetPoseType
    layers: list[AppearanceLayerPayload]
    restrictedZones: list[ZonePayload]


class ItemAppearancePayload(_BaseObject):
    layers: list[AppearanceLayerPayload]
    restrictedZones: list[ZonePayload]


class BaseItemPayload(_BaseObject):
    name: str
    description: str
    thumbnailUrl: str
    isNc: bool
    isPb: bool
    rarityIndex: str


class ItemPayload(BaseItemPayload):
    appearanceOn: ItemAppearancePayload | None


class UserPayload(_BaseObject):
    username: str


class OutfitPayload(_BaseObject):
    name: str | None
    petAppearance: PetAppearancePayload
    wornItems: list[ItemPayload]
    closetedItems: list[ItemPayload]
    creator: UserPayload | None
    createdAt: str
    updatedAt: str


# these are specific to the "fetch_neopet_by_name" http method.
class FetchedWornItemsPayload(_BaseObject):
    pass


class FetchedNeopetPayload(TypedDict):
    petAppearance: PetAppearancePayload
    wornItems: list[FetchedWornItemsPayload]


# specific to the "fetch_assets_for" http method
class FetchAssetsPayload(TypedDict):
    items: list[ItemPayload]
    petAppearance: PetAppearancePayload


# specific to the "fetch_all_appearances" http method
class ItemAllAppearancesPayload(BaseItemPayload):
    allAppearances: list[ItemAppearancePayload]


class CanonicalAppearancePayload(TypedDict):
    canonicalAppearance: PetAppearancePayload


class ColorAppliedToAllCompatibleSpeciesPayload(TypedDict):
    appliedToAllCompatibleSpecies: list[CanonicalAppearancePayload]


class FetchAllAppearancesPayload(TypedDict):
    items: list[ItemAllAppearancesPayload]
    color: ColorAppliedToAllCompatibleSpeciesPayload


ID = TypeVar("ID", bound=Union[str, int])
