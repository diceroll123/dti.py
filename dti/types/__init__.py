from typing import List, Literal, Optional, TypedDict

PetPoseType = Literal[
    "HAPPY_MASC",
    "HAPPY_FEM",
    "SAD_MASC",
    "SAD_FEM",
    "SICK_MASC",
    "SICK_FEM",
    "UNCONVERTED",
    "UKNOWN",
]


class SpeciesPayload(TypedDict):
    id: str
    name: str


class ColorPayload(TypedDict):
    id: str
    name: str


class ZonePayload(TypedDict):
    id: str
    depth: int
    label: str


class AppearanceLayerPayload(TypedDict):
    id: str
    imageUrl: str
    remoteId: str
    zone: ZonePayload
    knownGlitches: List[str]


class PetAppearancePayload(TypedDict):
    id: str
    bodyId: str
    isGlitched: bool
    color: ColorPayload
    species: SpeciesPayload
    pose: PetPoseType
    layers: List[AppearanceLayerPayload]
    restrictedZones: List[ZonePayload]


class ItemAppearancePayload(TypedDict):
    id: str
    layers: List[AppearanceLayerPayload]
    restrictedZones: List[ZonePayload]


class ItemPayload(TypedDict):
    id: str
    name: str
    description: str
    thumbnailUrl: str
    isNc: bool
    isPb: bool
    rarityIndex: str
    wakaValueText: str
    appearanceOn: Optional[ItemAppearancePayload]


class UserPayload(TypedDict):
    id: str
    username: str


class OutfitPayload(TypedDict):
    id: str
    name: Optional[str]
    petAppearance: PetAppearancePayload
    wornItems: List[ItemPayload]
    closetedItems: List[ItemPayload]
    creator: Optional[UserPayload]
    createdAt: str
    updatedAt: str
