import random
from enum import Enum, auto

__all__ = (
    "LayerImageSize",
    "PetPose",
    "ItemKind",
    "AppearanceLayerType",
    "AppearanceLayerKnownGlitch",
    "try_enum",
)

from typing import Any


class _DTIEnum(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    @classmethod
    def _missing_(cls, value):
        return cls[value]

    def __str__(self):
        return self.name

    def __int__(self):
        return int(self.value)


class ItemKind(_DTIEnum):
    NC = auto()
    NP = auto()
    PB = auto()


class LayerImageSize(_DTIEnum):
    """Represents the desired render size of a customization, in pixels."""

    SIZE_600 = auto()
    SIZE_300 = auto()
    SIZE_150 = auto()


class AppearanceLayerType(_DTIEnum):
    """Represents the type of appearance layer, whether it's for a pet or an item."""

    BIOLOGY = auto()
    OBJECT = auto()


class PetPose(int, _DTIEnum):
    """Represents a single pet pose. Each pose has an associated power-of-two value to easily
    create :class:`BitField` objects. This object acts like an :class:`int`.
    """

    HAPPY_MASC = 1
    SAD_MASC = 2
    SICK_MASC = 4
    HAPPY_FEM = 8
    SAD_FEM = 16
    SICK_FEM = 32
    UNCONVERTED = 64
    UNKNOWN = 128

    @classmethod
    def ideal(cls):
        return random.choice([cls.HAPPY_FEM, cls.HAPPY_MASC])

    @classmethod
    def all_fem(cls):
        return cls.SICK_FEM | cls.SAD_FEM | cls.HAPPY_FEM

    @classmethod
    def all_masc(cls):
        return cls.SICK_MASC | cls.SAD_MASC | cls.HAPPY_MASC


class AppearanceLayerKnownGlitch(Enum):
    OFFICIAL_SWF_IS_INCORRECT = "OFFICIAL_SWF_IS_INCORRECT"
    OFFICIAL_SVG_IS_INCORRECT = "OFFICIAL_SVG_IS_INCORRECT"
    OFFICIAL_MOVIE_IS_INCORRECT = "OFFICIAL_MOVIE_IS_INCORRECT"
    DISPLAYS_INCORRECTLY_BUT_CAUSE_UNKNOWN = "DISPLAYS_INCORRECTLY_BUT_CAUSE_UNKNOWN"
    OFFICIAL_BODY_ID_IS_INCORRECT = "OFFICIAL_BODY_ID_IS_INCORRECT"
    REQUIRES_OTHER_BODY_SPECIFIC_ASSETS = "REQUIRES_OTHER_BODY_SPECIFIC_ASSETS"


def try_enum(cls, val) -> Any:
    try:
        return cls(val)
    except TypeError:
        return val
